from contextlib import contextmanager
import logging
import os

logger = logging.getLogger(__name__)


def setup_telemetry(app=None, service_name: str = "ssuljaengi") -> None:
    endpoint = os.getenv("PHOENIX_OTEL_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except Exception as exc:  # noqa: BLE001
        logger.warning("telemetry_disabled reason=%s", exc)
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)

    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor

        LangChainInstrumentor().instrument()
    except Exception:
        logger.info("langchain_instrumentation_unavailable")

    if app is not None:
        try:
            FastAPIInstrumentor().instrument_app(app)
        except Exception:
            logger.info("fastapi_instrumentation_unavailable")


@contextmanager
def trace_span(name: str, **attributes):
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("ssuljaengi")
        with tracer.start_as_current_span(name) as span:
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, value)
            yield span
    except Exception:
        yield None
