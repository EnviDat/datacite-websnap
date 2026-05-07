"""Tests for src/datacite-websnap/exporter.py"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from botocore.exceptions import ClientError, BotoCoreError

import requests

from datacite_websnap.exporter import (
    decode_base64_xml,
    CustomClickException,
    _UploadProgress,
    format_xml_file_name,
    format_json_file_name,
    write_local_file,
    s3_client_put_object,
    create_s3_client,
    stream_url_to_s3,
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


def test_format_xml_file_name_with_colon():
    doi = "10.24435/materialscloud:2017.0005/v1"
    result = format_xml_file_name(doi)
    assert result == "10.24435_materialscloud_2017.0005_v1.xml"


def test_format_json_file_name():
    assert (
        format_json_file_name("10.16904_envidat.31.xml") == "10.16904_envidat.31.json"
    )


def test_format_json_file_name_with_prefix():
    assert (
        format_json_file_name("data/10.16904_envidat.31.xml")
        == "data/10.16904_envidat.31.json"
    )


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


# --- _UploadProgress ---


@patch("click.echo")
def test_upload_progress_with_total_bytes(mock_echo):
    progress = _UploadProgress(total_bytes=2 * 1024 * 1024)  # 2 MB total
    progress(1 * 1024 * 1024)  # 1 MB chunk

    mock_echo.assert_called_once_with("\r  Progress: 1.0 / 2.0 MB", nl=False)


@patch("click.echo")
def test_upload_progress_without_total_bytes(mock_echo):
    progress = _UploadProgress()
    progress(512 * 1024)  # 0.5 MB chunk

    mock_echo.assert_called_once_with("\r  Progress: 0.5 MB", nl=False)


@patch("click.echo")
def test_upload_progress_accumulates_across_calls(mock_echo):
    progress = _UploadProgress(total_bytes=3 * 1024 * 1024)  # 3 MB total
    progress(1 * 1024 * 1024)  # 1 MB chunk
    progress(1 * 1024 * 1024)  # another 1 MB chunk

    assert mock_echo.call_count == 2
    first_call, second_call = mock_echo.call_args_list
    assert first_call == (("\r  Progress: 1.0 / 3.0 MB",), {"nl": False})
    assert second_call == (("\r  Progress: 2.0 / 3.0 MB",), {"nl": False})


# --- stream_url_to_s3 ---


@patch("datacite_websnap.exporter.CustomEcho")
@patch("click.echo")
@patch("datacite_websnap.exporter.requests.get")
def test_stream_url_to_s3_success_with_content_length(mock_get, mock_echo, mock_custom_echo):
    mock_response = MagicMock()
    mock_response.headers = {"Content-Length": str(2 * 1024 * 1024)}
    mock_get.return_value = mock_response

    mock_s3 = MagicMock()

    stream_url_to_s3("https://example.com/file.csv", "my-bucket", "prefix/file.csv", mock_s3)

    mock_get.assert_called_once_with("https://example.com/file.csv", stream=True, timeout=(10, 60))
    mock_response.raise_for_status.assert_called_once()
    assert mock_response.raw.decode_content is True
    mock_s3.upload_fileobj.assert_called_once()
    call_kwargs = mock_s3.upload_fileobj.call_args.kwargs
    assert call_kwargs["Bucket"] == "my-bucket"
    assert call_kwargs["Key"] == "prefix/file.csv"
    assert isinstance(call_kwargs["Callback"], _UploadProgress)
    assert call_kwargs["Callback"]._total_bytes == 2 * 1024 * 1024
    mock_echo.assert_called_once_with()  # progress line terminator
    mock_custom_echo.assert_called_once()


@patch("datacite_websnap.exporter.CustomEcho")
@patch("click.echo")
@patch("datacite_websnap.exporter.requests.get")
def test_stream_url_to_s3_success_no_content_length(mock_get, mock_echo, mock_custom_echo):
    mock_response = MagicMock()
    mock_response.headers = {}
    mock_get.return_value = mock_response

    mock_s3 = MagicMock()

    stream_url_to_s3("https://example.com/file.csv", "my-bucket", "prefix/file.csv", mock_s3)

    call_kwargs = mock_s3.upload_fileobj.call_args.kwargs
    assert call_kwargs["Callback"]._total_bytes == 0


@patch("datacite_websnap.exporter.CustomWarning")
@patch("datacite_websnap.exporter.requests.get")
def test_stream_url_to_s3_timeout(mock_get, mock_warning):
    mock_get.side_effect = requests.exceptions.Timeout()

    stream_url_to_s3("https://example.com/file.csv", "my-bucket", "key", MagicMock())

    mock_warning.assert_called_once()
    assert "timed out" in mock_warning.call_args.args[0]


@patch("datacite_websnap.exporter.CustomWarning")
@patch("datacite_websnap.exporter.requests.get")
def test_stream_url_to_s3_http_error(mock_get, mock_warning):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    mock_get.return_value = mock_response

    stream_url_to_s3("https://example.com/file.csv", "my-bucket", "key", MagicMock())

    mock_warning.assert_called_once()
    assert "HTTP error" in mock_warning.call_args.args[0]


@patch("datacite_websnap.exporter.CustomWarning")
@patch("datacite_websnap.exporter.requests.get")
def test_stream_url_to_s3_request_exception(mock_get, mock_warning):
    mock_get.side_effect = requests.exceptions.RequestException("connection failed")

    stream_url_to_s3("https://example.com/file.csv", "my-bucket", "key", MagicMock())

    mock_warning.assert_called_once()
    assert "Error fetching" in mock_warning.call_args.args[0]


@patch("datacite_websnap.exporter.CustomWarning")
@patch("datacite_websnap.exporter.requests.get")
def test_stream_url_to_s3_unexpected_exception(mock_get, mock_warning):
    mock_get.side_effect = Exception("something unexpected")

    stream_url_to_s3("https://example.com/file.csv", "my-bucket", "key", MagicMock())

    mock_warning.assert_called_once()
    assert "Unexpected error" in mock_warning.call_args.args[0]
