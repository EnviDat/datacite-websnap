"""Tests for src/datacite-websnap/validators.py"""

import pytest
from click import BadParameter

from datacite_websnap.validators import (
    validate_url,
    validate_positive_int,
    validate_at_least_one_query_param,
    validate_bucket,
    validate_directory_path,
    validate_key_prefix,
    validate_single_string_key_value,
    CustomBadParameter,
    CustomClickException,
    validate_endpoint_url,
)


# --- validate_url ---
def test_validate_url_valid():
    assert validate_url(None, None, "https://example.com") == "https://example.com"


def test_validate_url_invalid():
    with pytest.raises(BadParameter):
        validate_url(None, None, "http://example.com")


def test_validate_positive_int_valid():
    assert validate_positive_int(None, None, 10) == 10


def test_validate_positive_int_invalid():
    with pytest.raises(BadParameter):
        validate_positive_int(None, None, -5)


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


def test_validate_single_string_key_value_valid():
    validate_single_string_key_value({"key": "value"})


def test_validate_single_string_key_value_invalid_non_string():
    with pytest.raises(CustomClickException):
        validate_single_string_key_value({1: "value"})


def test_validate_single_string_key_value_invalid_multiple_pairs():
    with pytest.raises(CustomClickException):
        validate_single_string_key_value({"a": "b", "c": "d"})
