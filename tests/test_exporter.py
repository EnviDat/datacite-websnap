"""Tests for src/datacite-websnap/exporter.py"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from botocore.exceptions import BotoCoreError, ClientError

from datacite_websnap.exporter import (
    decode_base64_xml,
    CustomClickException,
    format_xml_file_name,
    create_s3_client,
    write_local_file,
    s3_client_put_object,
)
from datacite_websnap.validators import S3ConfigModel


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
            decode_base64_xml("some_base64_string", file_logs=False)


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


@patch("boto3.Session")
def test_create_s3_client_success(mock_boto3_session):
    # Given a valid S3ConfigModel
    conf_s3 = S3ConfigModel(
        aws_access_key_id="fake_access_key",
        aws_secret_access_key="fake_secret_key",
        endpoint_url="http://fake-s3-endpoint.com",
    )

    # Mock the client creation
    mock_client = MagicMock()
    mock_boto3_session.return_value.client.return_value = mock_client

    # When calling the create_s3_client function
    result = create_s3_client(conf_s3)

    # Then it should return a valid boto3 client
    assert result == mock_client


@patch("boto3.Session")
def test_create_s3_client_failure(mock_boto3_session):
    """Test that CustomClickException is raised if boto3 client creation fails."""

    # Arrange
    conf_s3 = S3ConfigModel(
        aws_access_key_id="invalid_key",
        aws_secret_access_key="invalid_secret",
        endpoint_url="http://fake-s3-endpoint.com",
    )

    # Mock the session to raise an exception on client creation
    mock_session = MagicMock()
    mock_session.client.side_effect = BotoCoreError()
    mock_boto3_session.return_value = mock_session

    # Act & Assert
    with pytest.raises(CustomClickException):
        create_s3_client(conf_s3)


@patch("boto3.Session.client")
def test_s3_client_put_object_success(mock_boto3_client):
    mock_client = MagicMock()

    # Simulate a successful response from the S3 client (HTTP status code 200)
    mock_client.put_object.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200}  # Successful status code
    }
    mock_boto3_client.return_value = mock_client

    body = b"<xml>success</xml>"
    bucket = "test-bucket"
    key = "test_key.xml"

    # Act
    s3_client_put_object(
        client=mock_client, body=body, bucket=bucket, key=key, file_logs=True
    )

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
            file_logs=True,
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
            file_logs=True,
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
            file_logs=False,
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
        write_local_file(b"data", "file.xml", directory_path="/fake", file_logs=True)

    assert "IOError" in str(exc.value)


@patch("builtins.open", new_callable=mock_open)
def test_write_local_file_generic_exception(mock_open_fn):
    # Simulate generic error when writing
    mock_open_fn.side_effect = Exception("Something went wrong")

    with pytest.raises(CustomClickException) as exc:
        write_local_file(b"data", "file.xml", file_logs=True)

    assert "Unexpected error" in str(exc.value)
