"""Tests for src/datacite-websnap/validators.py"""

import pytest
from click import BadParameter

from datacite_websnap.validators import (
    validate_doi,
    validate_url,
    validate_page_size,
    validate_at_least_one_query_param,
    validate_bucket,
    validate_directory_path,
    validate_key_prefix,
    CustomBadParameter,
    validate_endpoint_url,
)


def test_validate_doi_bare_doi():
    assert validate_doi(None, None, "10.16904/envidat.504") == "10.16904/envidat.504"


def test_validate_doi_url():
    assert (
        validate_doi(None, None, "https://www.doi.org/10.16904/envidat.504")
        == "10.16904/envidat.504"
    )


def test_validate_doi_missing_slash():
    with pytest.raises(BadParameter, match="does not have a '/'"):
        validate_doi(None, None, "10.16904")


def test_validate_doi_invalid_url():
    with pytest.raises(BadParameter, match="not a valid URL"):
        validate_doi(None, None, "http:///10.16904/envidat.504")


def test_validate_doi_unsupported_prefix():
    with pytest.raises(BadParameter, match="not one of the supported"):
        validate_doi(None, None, "10.9999/some-record")


def test_validate_doi_unsupported_prefix_url():
    with pytest.raises(BadParameter, match="not one of the supported"):
        validate_doi(None, None, "https://doi.org/10.9999/some-record")


def test_validate_url_valid():
    assert validate_url(None, None, "https://example.com") == "https://example.com"


def test_validate_url_invalid():
    with pytest.raises(BadParameter):
        validate_url(None, None, "http://example.com")


def test_validate_page_size_valid():
    assert validate_page_size(None, None, 10) == 10
    assert validate_page_size(None, None, 1000) == 1000


def test_validate_page_size_invalid():
    with pytest.raises(BadParameter):
        validate_page_size(None, None, -5)

    with pytest.raises(BadParameter):
        validate_page_size(None, None, 1001)


def test_validate_at_least_one_query_param_valid():
    validate_at_least_one_query_param(("10.1234",), None)
    validate_at_least_one_query_param(None, "client-id")


def test_validate_at_least_one_query_param_invalid():
    with pytest.raises(CustomBadParameter):
        validate_at_least_one_query_param((), None)


def test_validate_bucket_valid():
    assert validate_bucket("my-bucket", "S3") == "my-bucket"
    assert validate_bucket(None, "local") is None


def test_validate_bucket_invalid():
    with pytest.raises(CustomBadParameter):
        validate_bucket(None, "S3")


def test_validate_endpoint_url():
    assert validate_endpoint_url("https://cloud.com/", "S3") == "https://cloud.com/"
    assert validate_endpoint_url(None, "local") is None


def test_validate_endpoint_url_invalid():
    with pytest.raises(CustomBadParameter):
        validate_endpoint_url(None, "S3")


def test_validate_endpoint_url_invalid_url():
    with pytest.raises(CustomBadParameter):
        validate_endpoint_url("abc", "S3")


def test_validate_directory_path_valid():
    assert validate_directory_path("samples/abc", "local") == "samples/abc"
    assert validate_directory_path(None, "S3") is None


def test_validate_directory_path_invalid():
    with pytest.raises(CustomBadParameter):
        validate_directory_path(None, "local")


def test_validate_key_prefix_valid():
    validate_key_prefix(None, "local")
    validate_key_prefix("some-prefix", "S3")


def test_validate_key_prefix_invalid():
    with pytest.raises(CustomBadParameter):
        validate_key_prefix("not-allowed", "local")
