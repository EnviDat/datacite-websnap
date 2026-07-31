"""Tests for src/datacite-websnap/repositories/scicat.py"""

import pytest
from unittest.mock import patch
from pydantic import ValidationError

from datacite_websnap.logger import CustomClickException
from datacite_websnap.repositories.scicat import (
    _validate_scicat_doi_response,
    _parse_scicat_data_urls,
    _is_expired,
    extract_scicat_data_urls,
    write_local_scicat_data_urls,
)


# --- _validate_scicat_doi_response ---


def test_validate_scicat_doi_response_success():
    raw = {"distribution": [{"contentUrl": "https://example.com/file.h5"}]}
    result = _validate_scicat_doi_response(raw)
    assert result.distribution[0].contentUrl == "https://example.com/file.h5"


def test_validate_scicat_doi_response_invalid():
    raw = {"distribution": [{"name": "missing contentUrl"}]}
    with pytest.raises(CustomClickException, match="Unexpected response format"):
        _validate_scicat_doi_response(raw)


def test_validate_scicat_doi_response_raises_pydantic_validation_error_as_cause():
    raw = {"distribution": [{"name": "missing contentUrl"}]}
    with pytest.raises(CustomClickException) as exc_info:
        _validate_scicat_doi_response(raw)
    assert isinstance(exc_info.value.__cause__, ValidationError)


# --- _parse_scicat_data_urls ---


def test_parse_scicat_data_urls_excludes_s3_uri():
    scicat_json = {
        "distribution": [
            {
                "contentUrl": "s3://bucket/file.h5",
                "name": "S3 URI",
                "expires": "2026-12-31T00:00:00Z",
            },
            {
                "contentUrl": "https://example.com/file.h5",
                "name": "HTTP URI",
                "expires": "2026-12-31T00:00:00Z",
            },
        ]
    }
    result = _parse_scicat_data_urls(scicat_json)
    assert result == {"https://example.com/file.h5": "2026-12-31T00:00:00Z"}


def test_parse_scicat_data_urls_excludes_item_with_no_expires():
    scicat_json = {
        "distribution": [
            {"contentUrl": "https://example.com/file.h5", "name": "HTTP URI"},
        ]
    }
    result = _parse_scicat_data_urls(scicat_json)
    assert result == {}


def test_parse_scicat_data_urls_empty_distribution():
    result = _parse_scicat_data_urls({"distribution": []})
    assert result == {}


# --- _is_expired ---


def test_is_expired_past_date():
    assert _is_expired("2020-01-01T00:00:00Z") is True


def test_is_expired_future_date():
    assert _is_expired("2999-01-01T00:00:00Z") is False


def test_is_expired_with_milliseconds():
    assert _is_expired("2020-01-01T00:00:00.612Z") is True


def test_is_expired_no_timezone_assumes_utc():
    assert _is_expired("2020-01-01T00:00:00") is True


def test_is_expired_invalid_date_raises_value_error():
    with pytest.raises(ValueError, match="Invalid ISO 8601 date string"):
        _is_expired("not-a-date")


# --- extract_scicat_data_urls ---


def test_extract_scicat_data_urls_returns_unexpired():
    scicat_json = {
        "distribution": [
            {
                "contentUrl": "https://example.com/valid.h5",
                "name": "HTTP URI",
                "expires": "2999-01-01T00:00:00Z",
            },
        ]
    }
    result = extract_scicat_data_urls(scicat_json)
    assert result == ["https://example.com/valid.h5"]


def test_extract_scicat_data_urls_excludes_expired_and_warns():
    scicat_json = {
        "distribution": [
            {
                "contentUrl": "https://example.com/expired.h5",
                "name": "HTTP URI",
                "expires": "2020-01-01T00:00:00Z",
            },
        ]
    }
    with patch("datacite_websnap.repositories.scicat.custom_warning") as mock_warning:
        result = extract_scicat_data_urls(scicat_json)
        assert result == []
        mock_warning.assert_called_once()


def test_extract_scicat_data_urls_excludes_item_with_no_expires():
    scicat_json = {
        "distribution": [
            {"contentUrl": "https://example.com/no-expires.h5", "name": "HTTP URI"},
        ]
    }
    result = extract_scicat_data_urls(scicat_json)
    assert result == []


def test_extract_scicat_data_urls_unparseable_date_excluded_and_warns():
    scicat_json = {
        "distribution": [
            {
                "contentUrl": "https://example.com/bad-date.h5",
                "name": "HTTP URI",
                "expires": "not-a-date",
            },
        ]
    }
    with patch("datacite_websnap.repositories.scicat.custom_warning") as mock_warning:
        result = extract_scicat_data_urls(scicat_json)
        assert result == []
        mock_warning.assert_called_once()


def test_extract_scicat_data_urls_mixed_results():
    scicat_json = {
        "distribution": [
            {
                "contentUrl": "https://example.com/valid.h5",
                "name": "HTTP URI",
                "expires": "2999-01-01T00:00:00Z",
            },
            {
                "contentUrl": "https://example.com/expired.h5",
                "name": "HTTP URI",
                "expires": "2020-01-01T00:00:00Z",
            },
            {
                "contentUrl": "s3://bucket/file.h5",
                "name": "S3 URI",
                "expires": "2999-01-01T00:00:00Z",
            },
        ]
    }
    with patch("datacite_websnap.repositories.scicat.custom_warning"):
        result = extract_scicat_data_urls(scicat_json)
    assert result == ["https://example.com/valid.h5"]


# --- write_local_scicat_data_urls ---


@patch("datacite_websnap.repositories.scicat.write_local_file_data_links")
def test_write_local_scicat_data_urls_writes_valid_links(mock_write_local_file):
    scicat_json = {
        "distribution": [
            {
                "contentUrl": "https://example.com/valid.h5",
                "name": "HTTP URI",
                "expires": "2999-01-01T00:00:00Z",
            },
        ]
    }
    write_local_scicat_data_urls(scicat_json, "/tmp/doi_dir", "10.16907")

    mock_write_local_file.assert_called_once_with(
        "https://example.com/valid.h5", "/tmp/doi_dir", "10.16907"
    )


@patch("datacite_websnap.repositories.scicat.write_local_file_data_links")
def test_write_local_scicat_data_urls_no_valid_links(mock_write_local_file):
    scicat_json = {
        "distribution": [
            {
                "contentUrl": "https://example.com/expired.h5",
                "name": "HTTP URI",
                "expires": "2020-01-01T00:00:00Z",
            },
        ]
    }
    with patch("datacite_websnap.repositories.scicat.custom_warning"):
        write_local_scicat_data_urls(scicat_json, "/tmp/doi_dir", "10.16907")

    mock_write_local_file.assert_not_called()