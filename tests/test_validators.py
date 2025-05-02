"""Tests for src/datacite-websnap/validators.py"""

import pytest
from click import BadParameter
from unittest.mock import patch

from datacite_websnap.validators import (
    validate_url,
    validate_positive_int,
    validate_at_least_one_query_param,
    validate_bucket,
    validate_directory_path,
    validate_key_prefix,
    validate_single_string_key_value,
    validate_s3_config,
    CustomBadParameter,
    CustomClickException,
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


def test_validate_s3_config_valid(monkeypatch):
    monkeypatch.setenv("ENDPOINT_URL", "https://s3.amazonaws.com")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "abc")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "123")
    conf = validate_s3_config()
    assert str(conf.endpoint_url) == "https://s3.amazonaws.com/"
    assert conf.aws_access_key_id == "abc"
    assert conf.aws_secret_access_key == "123"


def test_validate_s3_config_validation_error():
    with (
        patch("datacite_websnap.validators.os.getenv", side_effect=lambda k: None),
    ):
        with pytest.raises(CustomClickException):
            validate_s3_config(file_logs=True)


def test_validate_s3_config_unexpected_error():
    with (
        patch(
            "datacite_websnap.validators.os.getenv", side_effect=Exception("unexpected")
        ),
    ):
        with pytest.raises(CustomClickException):
            validate_s3_config(file_logs=True)
