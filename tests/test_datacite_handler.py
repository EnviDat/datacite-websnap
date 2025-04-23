"""Tests for src/datacite-websnap/datacite_handler.py"""

import pytest
from unittest.mock import patch, MagicMock
import requests

from datacite_websnap.datacite_handler import (
    get_url_json,
    get_datacite_client,
    extract_doi_xml,
    get_datacite_list_dois_xml,
    CustomClickException,
)


def test_get_url_json_success():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"key": "value"}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = get_url_json("http://example.com")
        assert result == {"key": "value"}


def test_get_url_json_http_error():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        mock_get.return_value = mock_resp

        with pytest.raises(CustomClickException):
            get_url_json("http://example.com")


def test_get_url_json_connection_error():
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        with pytest.raises(CustomClickException):
            get_url_json("http://example.com")


def test_get_url_json_timeout():
    with patch("requests.get", side_effect=requests.exceptions.Timeout):
        with pytest.raises(CustomClickException):
            get_url_json("http://example.com")


def test_get_url_json_request_exception():
    with patch("requests.get", side_effect=requests.exceptions.RequestException):
        with pytest.raises(CustomClickException):
            get_url_json("http://example.com")


def test_get_url_json_generic_error():
    with patch("requests.get", side_effect=Exception("unexpected")):
        with pytest.raises(CustomClickException):
            get_url_json("http://example.com")


def test_get_datacite_client():
    with patch("datacite_websnap.datacite_handler.get_url_json") as mock_get:
        mock_get.return_value = {"client": "data"}
        result = get_datacite_client("https://api.example.org", "client123")
        assert result == {"client": "data"}


def test_extract_doi_xml_valid():
    data = {
        "data": [
            {"attributes": {"doi": "10.123/abc", "xml": "<xml1>"}},
            {"attributes": {"doi": "10.123/def", "xml": "<xml2>"}},
        ]
    }
    expected = [{"10.123/abc": "<xml1>"}, {"10.123/def": "<xml2>"}]
    assert extract_doi_xml(data) == expected


def test_extract_doi_xml_missing_fields():
    data = {"data": [{"attributes": {"doi": "10.123/abc"}}]}
    assert extract_doi_xml(data) == []


def test_get_datacite_list_dois_xml_single_page():
    mock_response = {
        "meta": {"total": 2, "totalPages": 1},
        "links": {},
        "data": [
            {"attributes": {"doi": "10.123/abc", "xml": "<xml1>"}},
            {"attributes": {"doi": "10.123/def", "xml": "<xml2>"}},
        ],
    }

    with patch(
        "datacite_websnap.datacite_handler.get_url_json", return_value=mock_response
    ):
        with patch("datacite_websnap.datacite_handler.CustomEcho"):
            results = get_datacite_list_dois_xml(
                api_url="https://api.example.org",
                client_id="client123",
                doi_prefix=("abc", "def"),
                file_logs=False,
            )
            assert len(results) == 2
            assert {"10.123/abc": "<xml1>"} in results


def test_get_datacite_list_dois_xml_zero_records():
    mock_response = {
        "meta": {"total": 0, "totalPages": 1},
        "links": {},
        "data": [],
    }

    with patch(
        "datacite_websnap.datacite_handler.get_datacite_dois",
        return_value=mock_response,
    ):
        with pytest.raises(CustomClickException):
            get_datacite_list_dois_xml(
                api_url="https://api.example.org",
                client_id="test-client",
                file_logs=False,
            )


def test_get_datacite_list_dois_xml_multiple_pages():
    first_page = {
        "meta": {"total": 4, "totalPages": 2},
        "links": {"next": "https://next.page"},
        "data": [
            {"attributes": {"doi": "10.123/abc", "xml": "<xml1>"}},
            {"attributes": {"doi": "10.123/def", "xml": "<xml2>"}},
        ],
    }

    second_page = {
        "meta": {"total": 4, "totalPages": 2},
        "links": {},
        "data": [
            {"attributes": {"doi": "10.123/ghi", "xml": "<xml3>"}},
            {"attributes": {"doi": "10.123/jkl", "xml": "<xml4>"}},
        ],
    }

    with patch(
        "datacite_websnap.datacite_handler.get_datacite_dois", return_value=first_page
    ):
        with patch(
            "datacite_websnap.datacite_handler.get_url_json", return_value=second_page
        ):
            result = get_datacite_list_dois_xml(
                api_url="https://api.example.org",
                client_id="test-client",
                file_logs=False,
            )

    expected = [
        {"10.123/abc": "<xml1>"},
        {"10.123/def": "<xml2>"},
        {"10.123/ghi": "<xml3>"},
        {"10.123/jkl": "<xml4>"},
    ]

    assert result == expected


def test_get_datacite_list_dois_xml_mismatched_total_records():
    first_page = {
        "meta": {"total": 3, "totalPages": 1},
        "links": {},
        "data": [
            {"attributes": {"doi": "10.123/abc", "xml": "<xml1>"}},
            {"attributes": {"doi": "10.123/def", "xml": "<xml2>"}},
        ],
    }

    with patch(
        "datacite_websnap.datacite_handler.get_datacite_dois", return_value=first_page
    ):
        with pytest.raises(CustomClickException):
            get_datacite_list_dois_xml(
                api_url="https://api.example.org",
                client_id="test-client",
                file_logs=False,
            )
