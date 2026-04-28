"""Tests for src/datacite-websnap/exporter.py"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from botocore.exceptions import ClientError, BotoCoreError

from datacite_websnap.exporter import (
    decode_base64_xml,
    CustomClickException,
    format_xml_file_name,
    write_local_file,
    s3_client_put_object,
    create_s3_client,
)


def test_decode_base64_xml_valid():
    # Given a valid base64 encoded string
    encoded_xml = "PHhtbD48L3htbD4="  # This is base64 for "<xml></xml>"
    result = decode_base64_xml(encoded_xml)
    assert result == b"<xml></xml>"


def test_decode_base64_xml_invalid():
    # Given an invalid base64 string that will raise UnicodeDecodeError
    encoded_xml = "invalid_base64_string"
    with pytest.raises(CustomClickException):
        decode_base64_xml(encoded_xml)


def test_decode_base64_xml_unexpected_exception():
    # Patch base64.b64decode to raise an unexpected exception
    with patch("base64.b64decode") as mock_b64decode:
        # Set the mock to raise a ValueError when called
        mock_b64decode.side_effect = ValueError("Unexpected ValueError")

        # Call the function with a valid base64 string
        with pytest.raises(CustomClickException):
            decode_base64_xml("some_base64_string")


def test_format_xml_file_name_no_prefix():
    doi = "10.16904/envidat.31"
    result = format_xml_file_name(doi)
    assert result == "10.16904_envidat.31.xml"


def test_format_xml_file_name_with_prefix():
    doi = "10.16904/envidat.31"
    key_prefix = "data/"
    result = format_xml_file_name(doi, key_prefix)
    assert result == "data/10.16904_envidat.31.xml"


def test_format_xml_file_name_with_prefix_no_trailing_slash():
    doi = "10.16904/envidat.31"
    key_prefix = "data"
    result = format_xml_file_name(doi, key_prefix)
    assert result == "data/10.16904_envidat.31.xml"


@patch("boto3.Session.client")
def test_s3_client_put_object_success(mock_boto3_client):
    mock_client = MagicMock()

    # Simulate a successful response from the S3 client (HTTP status code 200)
    mock_client.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_boto3_client.return_value = mock_client

    body = b"<xml>success</xml>"
    bucket = "test-bucket"
    key = "test_key.xml"

    s3_client_put_object(client=mock_client, body=body, bucket=bucket, key=key)

    mock_client.put_object.assert_called_once_with(Body=body, Bucket=bucket, Key=key)


def test_s3_client_put_object_client_error():
    mock_client = MagicMock()
    mock_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "InternalError"}}, "PutObject"
    )

    with pytest.raises(CustomClickException):
        s3_client_put_object(
            client=mock_client,
            body=b"<xml>error</xml>",
            bucket="test-bucket",
            key="fail.xml",
        )


def test_s3_client_put_object_exception():
    mock_client = MagicMock()
    mock_client.put_object.side_effect = Exception(
        "Something weird happened", "PutObject"
    )

    with pytest.raises(CustomClickException):
        s3_client_put_object(
            client=mock_client,
            body=b"<xml>error</xml>",
            bucket="test-bucket",
            key="fail.xml",
        )


def test_s3_client_put_object_non_200_status():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 500}}

    with pytest.raises(CustomClickException):
        s3_client_put_object(
            client=mock_client,
            body=b"<xml>fail</xml>",
            bucket="test-bucket",
            key="bad_status.xml",
        )


def test_s3_client_put_object_missing_response_metadata():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}

    with pytest.raises(CustomClickException, match="Missing ResponseMetadata"):
        s3_client_put_object(
            client=mock_client,
            body=b"<xml>fail</xml>",
            bucket="test-bucket",
            key="missing_metadata.xml",
        )


def test_write_local_file_success(tmp_path):
    content = b"<xml>test</xml>"
    filename = "test.xml"
    file_path = tmp_path / filename

    write_local_file(content, filename, directory_path=str(tmp_path))

    assert file_path.exists()
    assert file_path.read_bytes() == content


@patch("builtins.open", new_callable=mock_open)
def test_write_local_file_ioerror(mock_open_fn):
    # Simulate IOError when opening file
    mock_open_fn.side_effect = IOError("Disk full")

    with pytest.raises(CustomClickException) as exc:
        write_local_file(b"data", "file.xml", directory_path="/fake")

    assert "IOError" in str(exc.value)


@patch("builtins.open", new_callable=mock_open)
def test_write_local_file_generic_exception(mock_open_fn):
    # Simulate generic error when writing
    mock_open_fn.side_effect = Exception("Something went wrong")

    with pytest.raises(CustomClickException) as exc:
        write_local_file(b"data", "file.xml")

    assert "Unexpected error" in str(exc.value)


@patch("boto3.Session")
def test_create_s3_client_success(mock_session_class):
    # Setup mocks
    mock_session_inst = MagicMock()
    mock_client = MagicMock()
    mock_session_class.return_value = mock_session_inst
    mock_session_inst.client.return_value = mock_client

    # Execute
    endpoint = "https://example.com"
    bucket = "my-test-bucket"
    result = create_s3_client(endpoint, bucket, profile_name="dev")

    # Assertions
    mock_session_class.assert_called_once_with(profile_name="dev")
    mock_session_inst.client.assert_called_once()
    mock_client.head_bucket.assert_called_once_with(Bucket=bucket)
    assert result == mock_client


@patch("boto3.Session")
def test_create_s3_client_connection_error(mock_session_class):
    # Simulate a BotoCoreError during session/client creation
    mock_session_class.side_effect = BotoCoreError()

    with pytest.raises(CustomClickException) as exc:
        create_s3_client("http://invalid", "bucket")

    assert "Failed to create S3 client" in str(exc.value)


@patch("boto3.Session")
def test_create_s3_client_invalid_bucket(mock_session_class):
    # Setup mocks to fail at head_bucket
    mock_session_inst = MagicMock()
    mock_client = MagicMock()
    mock_session_class.return_value = mock_session_inst
    mock_session_inst.client.return_value = mock_client

    # Simulate a 404/403 ClientError
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mock_client.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

    with pytest.raises(CustomClickException) as exc:
        create_s3_client("http://valid", "nonexistent-bucket")

    assert "S3 credentials, endpoint and/or bucket are invalid" in str(exc.value)
