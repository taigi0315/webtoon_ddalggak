"""Tests for Gemini client error handling and graceful degradation."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.services.vertex_gemini import (
    CircuitBreakerState,
    GeminiError,
    GeminiRateLimitError,
    GeminiContentFilterError,
    GeminiTimeoutError,
    GeminiCircuitOpenError,
    GeminiModelUnavailableError,
    GeminiClient,
)


class TestCircuitBreakerState:
    """Tests for CircuitBreakerState."""

    def test_initial_state_is_closed(self):
        cb = CircuitBreakerState()
        assert not cb.is_open
        assert not cb.is_half_open
        assert cb.failure_count == 0

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreakerState(failure_threshold=3)

        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert cb.is_open

    def test_half_open_after_timeout(self):
        cb = CircuitBreakerState(failure_threshold=2, recovery_timeout_seconds=1)

        cb.record_failure()
        cb.record_failure()
        assert cb.is_open

        # Simulate time passing
        cb.circuit_open_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert not cb.is_open
        assert cb.is_half_open

    def test_closes_after_successes_in_half_open(self):
        cb = CircuitBreakerState(
            failure_threshold=2,
            recovery_timeout_seconds=1,
            half_open_success_threshold=2,
        )

        cb.record_failure()
        cb.record_failure()

        # Move to half-open state
        cb.circuit_open_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert cb.is_half_open

        cb.record_success()
        assert cb.is_half_open  # Still half-open after 1 success

        cb.record_success()
        assert not cb.is_half_open  # Now closed
        assert cb.failure_count == 0

    def test_check_circuit_raises_when_open(self):
        cb = CircuitBreakerState(failure_threshold=1)
        cb.record_failure()

        with pytest.raises(GeminiCircuitOpenError) as exc_info:
            cb.check_circuit()

        assert "Circuit breaker is open" in str(exc_info.value)
        assert exc_info.value.retry_after is not None

    def test_reset_clears_state(self):
        cb = CircuitBreakerState(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()

        cb.reset()

        assert cb.failure_count == 0
        assert not cb.is_open
        assert cb.circuit_open_until is None


class TestGeminiClientErrorClassification:
    """Tests for error classification in GeminiClient."""

    @pytest.fixture
    def client(self):
        """Create a GeminiClient with mocked genai."""
        with patch("app.services.vertex_gemini.genai"):
            return GeminiClient(
                project=None,
                location=None,
                api_key="test-key",
                text_model="test-model",
                image_model="test-image-model",
            )

    def test_classifies_rate_limit_error(self, client):
        error_type, retryable = client._classify_error(
            Exception("RESOURCE_EXHAUSTED"),
            "RESOURCE_EXHAUSTED: quota exceeded",
        )
        assert error_type == "rate_limit"
        assert retryable is True

    def test_classifies_429_as_rate_limit(self, client):
        error_type, retryable = client._classify_error(
            Exception("429 Too Many Requests"),
            "429 Too Many Requests",
        )
        assert error_type == "rate_limit"
        assert retryable is True

    def test_classifies_content_filter_error(self, client):
        error_type, retryable = client._classify_error(
            Exception("Content blocked by SAFETY filter"),
            "Content blocked by SAFETY filter",
        )
        assert error_type == "content_filter"
        assert retryable is False

    def test_classifies_timeout_error(self, client):
        error_type, retryable = client._classify_error(
            Exception("Request timeout"),
            "Request timeout after 60s",
        )
        assert error_type == "timeout"
        assert retryable is True

    def test_classifies_model_unavailable(self, client):
        error_type, retryable = client._classify_error(
            Exception("503 Service Unavailable"),
            "503 Service Unavailable",
        )
        assert error_type == "model_unavailable"
        assert retryable is True

    def test_classifies_invalid_request(self, client):
        error_type, retryable = client._classify_error(
            Exception("400 Invalid request"),
            "400 Invalid request: malformed prompt",
        )
        assert error_type == "invalid_request"
        assert retryable is False


class TestGeminiClientCircuitBreaker:
    """Tests for circuit breaker integration in GeminiClient."""

    @pytest.fixture
    def client(self):
        """Create a GeminiClient with low threshold for testing."""
        with patch("app.services.vertex_gemini.genai"):
            return GeminiClient(
                project=None,
                location=None,
                api_key="test-key",
                text_model="test-model",
                image_model="test-image-model",
                circuit_breaker_threshold=2,
                circuit_breaker_timeout=60,
            )

    def test_get_circuit_breaker_status(self, client):
        status = client.get_circuit_breaker_status()

        assert "generate_text" in status
        assert "generate_image" in status
        assert status["generate_text"]["is_open"] is False
        assert status["generate_text"]["failure_count"] == 0

    def test_reset_circuit_breaker(self, client):
        # Manually trigger failures
        cb = client._circuit_breakers["generate_text"]
        cb.record_failure()
        cb.record_failure()

        assert cb.is_open

        client.reset_circuit_breaker("generate_text")

        assert not cb.is_open
        assert cb.failure_count == 0

    def test_reset_all_circuit_breakers(self, client):
        for cb in client._circuit_breakers.values():
            cb.record_failure()
            cb.record_failure()

        client.reset_circuit_breaker()

        for cb in client._circuit_breakers.values():
            assert not cb.is_open


class TestGeminiExceptionTypes:
    """Tests for custom exception types."""

    def test_gemini_error_has_request_id(self):
        exc = GeminiError("Test error", request_id="req-123", model="test-model")
        assert exc.request_id == "req-123"
        assert exc.model == "test-model"
        assert "Test error" in str(exc)

    def test_content_filter_error_has_categories(self):
        exc = GeminiContentFilterError(
            "Content blocked",
            blocked_categories=["HARM_CATEGORY_HARASSMENT"],
        )
        assert exc.blocked_categories == ["HARM_CATEGORY_HARASSMENT"]

    def test_circuit_open_error_has_retry_after(self):
        retry_time = datetime.now(timezone.utc) + timedelta(seconds=60)
        exc = GeminiCircuitOpenError("Circuit open", retry_after=retry_time)
        assert exc.retry_after == retry_time
