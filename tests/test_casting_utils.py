"""Tests for casting utility functions."""

import pytest

from app.api.v1.casting import _is_local_path


class TestIsLocalPath:
    def test_http_url(self):
        assert _is_local_path("http://example.com/image.png") is False

    def test_https_url(self):
        assert _is_local_path("https://example.com/image.png") is False

    def test_media_url(self):
        assert _is_local_path("/media/images/abc.png") is False

    def test_absolute_unix_path(self):
        assert _is_local_path("/home/user/image.png") is True

    def test_tilde_path(self):
        assert _is_local_path("~/images/character.png") is True

    def test_relative_path(self):
        assert _is_local_path("./images/character.png") is True

    def test_windows_path(self):
        assert _is_local_path("C:\\Users\\test\\image.png") is True

    def test_random_string_not_local(self):
        assert _is_local_path("just-a-name") is False
