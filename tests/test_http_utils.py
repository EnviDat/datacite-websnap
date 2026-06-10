"""Tests for src/datacite-websnap/http_utils.py"""

import pytest
from unittest.mock import patch, MagicMock
import requests

from datacite_websnap.http_utils import (
    get_url_json,
    get_url_content,
    get_url_content_length,
)
from datacite_websnap.logger import CustomClickException


# --- get_url_json ---


def test_get_url_json_success():
    with patch("datacite_websnap.http_utils.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"key": "value"}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = get_url_json("http://example.com")
        assert result == {"key": "value"}


def test_get_url_json_http_error():
    with patch("datacite_websnap.http_utils.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        mock_get.return_value = mock_resp

        with pytest.raises(CustomClickException):
            get_url_json("http://example.com")


@patch("datacite_websnap.http_utils.requests.get")
def test_get_url_json_decode_error(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError(
        "msg", "doc", 0
    )
    mock_get.return_value = mock_response

    with pytest.raises(CustomClickException) as exc_info:
        get_url_json("https://example.com")

    assert "Invalid response" in str(exc_info.value)
    assert "The server did not return valid JSON" in str(exc_info.value)


def test_get_url_json_connection_error():
    with patch(
        "datacite_websnap.http_utils.requests.get",
        side_effect=requests.exceptions.ConnectionError,
    ):
        with pytest.raises(CustomClickException):
            get_url_json("http://example.com")


def test_get_url_json_timeout():
    with patch(
        "datacite_websnap.http_utils.requests.get",
        side_effect=requests.exceptions.Timeout,
    ):
        with pytest.raises(CustomClickException):
            get_url_json("http://example.com")


def test_get_url_json_request_exception():
    with patch(
        "datacite_websnap.http_utils.requests.get",
        side_effect=requests.exceptions.RequestException,
    ):
        with pytest.raises(CustomClickException):
            get_url_json("http://example.com")


def test_get_url_json_generic_error():
    with patch(
        "datacite_websnap.http_utils.requests.get", side_effect=Exception("unexpected")
    ):
        with pytest.raises(CustomClickException):
            get_url_json("http://example.com")


# --- get_url_content ---


def test_get_url_content_success():
    with patch("datacite_websnap.http_utils.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.content = b"file content"
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        assert get_url_content("https://example.com/file.csv") == b"file content"


def test_get_url_content_http_error():
    with patch("datacite_websnap.http_utils.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        mock_get.return_value = mock_resp
        with pytest.raises(CustomClickException, match="HTTP error"):
            get_url_content("https://example.com/file.csv")


def test_get_url_content_401_returns_none_and_warns():
    mock_response = MagicMock()
    mock_response.status_code = 401
    http_error = requests.exceptions.HTTPError("401 Unauthorized")
    http_error.response = mock_response

    with patch("datacite_websnap.http_utils.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_resp

        with patch("datacite_websnap.http_utils.custom_warning") as mock_warning:
            result = get_url_content("https://example.com/file.csv")
            assert result is None
            mock_warning.assert_called_once()


def test_get_url_content_non_401_http_error_raises():
    mock_response = MagicMock()
    mock_response.status_code = 403
    http_error = requests.exceptions.HTTPError("403 Forbidden")
    http_error.response = mock_response

    with patch("datacite_websnap.http_utils.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_resp

        with pytest.raises(CustomClickException, match="HTTP error"):
            get_url_content("https://example.com/file.csv")


def test_get_url_content_connection_error():
    with patch(
        "datacite_websnap.http_utils.requests.get",
        side_effect=requests.exceptions.ConnectionError,
    ):
        with pytest.raises(CustomClickException, match="Network error"):
            get_url_content("https://example.com/file.csv")


def test_get_url_content_timeout():
    with patch(
        "datacite_websnap.http_utils.requests.get",
        side_effect=requests.exceptions.Timeout,
    ):
        with pytest.raises(CustomClickException, match="Request timeout"):
            get_url_content("https://example.com/file.csv")


def test_get_url_content_request_exception():
    with patch(
        "datacite_websnap.http_utils.requests.get",
        side_effect=requests.exceptions.RequestException,
    ):
        with pytest.raises(CustomClickException, match="Request failed"):
            get_url_content("https://example.com/file.csv")


def test_get_url_content_unexpected_exception():
    with patch(
        "datacite_websnap.http_utils.requests.get", side_effect=Exception("unexpected")
    ):
        with pytest.raises(CustomClickException, match="Unexpected error"):
            get_url_content("https://example.com/file.csv")


# --- get_url_content_length ---


def test_get_url_content_length_with_header():
    mock_response = MagicMock()
    mock_response.headers = {"Content-Length": "2048"}
    with patch("datacite_websnap.http_utils.requests.head", return_value=mock_response):
        assert get_url_content_length("https://example.com/file.csv") == 2048


def test_get_url_content_length_no_header():
    mock_response = MagicMock()
    mock_response.headers = {}
    with patch("datacite_websnap.http_utils.requests.head", return_value=mock_response):
        assert get_url_content_length("https://example.com/file.csv") == 0


def test_get_url_content_length_request_exception():
    with patch(
        "datacite_websnap.http_utils.requests.head",
        side_effect=requests.exceptions.RequestException("timeout"),
    ):
        assert get_url_content_length("https://example.com/file.csv") == 0


def test_get_url_content_length_custom_timeout():
    mock_response = MagicMock()
    mock_response.headers = {"Content-Length": "512"}
    with patch(
        "datacite_websnap.http_utils.requests.head", return_value=mock_response
    ) as mock_head:
        get_url_content_length("https://example.com/file.csv", timeout=(3, 30))
        mock_head.assert_called_once_with(
            "https://example.com/file.csv", timeout=(3, 30), allow_redirects=True
        )
