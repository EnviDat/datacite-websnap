"""Tests for src/datacite-websnap/exporter.py"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from botocore.exceptions import ClientError, BotoCoreError

import requests

from datacite_websnap.logger import CustomClickException
from datacite_websnap.exporter import (
    decode_base64_xml,
    _UploadProgress,
    format_xml_file_name,
    format_json_file_name,
    format_size,
    write_local_file,
    write_local_file_data_links,
    s3_client_put_object,
    create_s3_client,
    stream_url_to_s3,
    resolve_data_link,
    echo_resolved_data_links,
    upload_data_link,
    s3_key_exists,
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
    with patch("datacite_websnap.exporter.base64.b64decode") as mock_b64decode:
        mock_b64decode.side_effect = ValueError("Unexpected ValueError")
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


# --- format_size ---


def test_format_size_zero():
    assert format_size(0) == "size unknown"


def test_format_size_kb():
    assert format_size(512) == "0.5 KB"


def test_format_size_mb():
    assert format_size(512 * 1024**2) == "512.0 MB"


def test_format_size_mb_boundary():
    assert format_size(1024**3 - 1) == "1024.0 MB"


def test_format_size_gb_exact():
    assert format_size(1024**3) == "1.0 GB"


def test_format_size_gb():
    assert format_size(int(2.5 * 1024**3)) == "2.5 GB"


def test_s3_client_put_object_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

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

    mock_echo.assert_called_once_with("\r  Progress: 1.0 MB / 2.0 MB", nl=False)


@patch("click.echo")
def test_upload_progress_without_total_bytes(mock_echo):
    progress = _UploadProgress()
    progress(512 * 1024)  # 0.5 MB chunk

    mock_echo.assert_called_once_with("\r  Progress: 512.0 KB", nl=False)


@patch("click.echo")
def test_upload_progress_accumulates_across_calls(mock_echo):
    progress = _UploadProgress(total_bytes=3 * 1024 * 1024)  # 3 MB total
    progress(1 * 1024 * 1024)  # 1 MB chunk
    progress(1 * 1024 * 1024)  # another 1 MB chunk

    assert mock_echo.call_count == 2
    first_call, second_call = mock_echo.call_args_list
    assert first_call == (("\r  Progress: 1.0 MB / 3.0 MB",), {"nl": False})
    assert second_call == (("\r  Progress: 2.0 MB / 3.0 MB",), {"nl": False})


# --- stream_url_to_s3 ---


@patch("datacite_websnap.exporter.CustomEcho")
@patch("datacite_websnap.exporter.click.echo")
@patch("datacite_websnap.exporter.requests.get")
def test_stream_url_to_s3_success_with_content_length(
    mock_get, mock_echo, mock_custom_echo
):
    mock_response = MagicMock()
    mock_response.headers = {"Content-Length": str(2 * 1024 * 1024)}
    mock_get.return_value = mock_response

    mock_s3 = MagicMock()

    stream_url_to_s3(
        "https://example.com/file.csv",
        "my-bucket",
        "prefix/file.csv",
        mock_s3,
        show_upload_progress=True,
    )

    mock_get.assert_called_once_with(
        "https://example.com/file.csv", stream=True, timeout=(10, 60)
    )
    mock_response.raise_for_status.assert_called_once()
    assert mock_response.raw.decode_content is True
    mock_s3.upload_fileobj.assert_called_once()
    call_kwargs = mock_s3.upload_fileobj.call_args.kwargs
    assert call_kwargs["Bucket"] == "my-bucket"
    assert call_kwargs["Key"] == "prefix/file.csv"
    assert isinstance(call_kwargs["Callback"], _UploadProgress)
    assert call_kwargs["Callback"]._total_bytes == 2 * 1024 * 1024
    from unittest.mock import call

    assert call() in mock_echo.call_args_list  # progress line terminator
    mock_custom_echo.assert_called_once()


@patch("datacite_websnap.exporter.CustomEcho")
@patch("click.echo")
@patch("datacite_websnap.exporter.requests.get")
def test_stream_url_to_s3_success_no_content_length(
    mock_get, mock_echo, mock_custom_echo
):
    mock_response = MagicMock()
    mock_response.headers = {}
    mock_get.return_value = mock_response

    mock_s3 = MagicMock()

    stream_url_to_s3(
        "https://example.com/file.csv",
        "my-bucket",
        "prefix/file.csv",
        mock_s3,
        show_upload_progress=True,
    )

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


# --- resolve_data_link ---


@patch("datacite_websnap.exporter.get_envicloud_objects")
def test_resolve_data_link_envicloud(mock_get_envicloud):
    mock_get_envicloud.return_value = [
        ("data/file1.csv", "https://s3.wsl.ch/envidat/data/file1.csv", 1024),
        ("data/file2.nc", "https://s3.wsl.ch/envidat/data/file2.nc", 2048),
    ]

    result = resolve_data_link(
        "10.16904",
        "https://envicloud.wsl.ch/#/?bucket=https%3A%2F%2Fs3.wsl.ch%2Fenvidat&prefix=data%2F",
        "doi_dir",
    )

    assert result == [
        ("doi_dir/data/file1.csv", "https://s3.wsl.ch/envidat/data/file1.csv", 1024),
        ("doi_dir/data/file2.nc", "https://s3.wsl.ch/envidat/data/file2.nc", 2048),
    ]


@patch("datacite_websnap.exporter.get_envicloud_objects")
def test_resolve_data_link_envicloud_empty(mock_get_envicloud):
    mock_get_envicloud.return_value = []

    result = resolve_data_link(
        "10.16904",
        "https://envicloud.wsl.ch/#/?bucket=https%3A%2F%2Fs3.wsl.ch%2Fenvidat&prefix=data%2F",
        "doi_dir",
    )

    assert result == []


@patch("datacite_websnap.exporter.get_url_content_length", return_value=4096)
def test_resolve_data_link_regular_url_with_content_length(mock_size):
    result = resolve_data_link(
        "10.16904", "https://example.com/data/report.csv", "doi_dir"
    )

    assert result == [
        ("doi_dir/report.csv", "https://example.com/data/report.csv", 4096)
    ]
    mock_size.assert_called_once_with("https://example.com/data/report.csv")


@patch("datacite_websnap.exporter.get_url_content_length", return_value=0)
def test_resolve_data_link_regular_url_no_content_length(mock_size):
    result = resolve_data_link(
        "10.16904", "https://example.com/data/report.csv", "doi_dir"
    )

    assert result == [("doi_dir/report.csv", "https://example.com/data/report.csv", 0)]


@patch("datacite_websnap.exporter.get_url_content_length", return_value=0)
def test_resolve_data_link_regular_url_no_filename(mock_size):
    # URL with no filename in path (e.g. bare domain) returns empty list
    result = resolve_data_link("10.16904", "https://example.com/", "doi_dir")

    assert result == []


@patch("datacite_websnap.exporter.CustomWarning")
def test_resolve_data_link_unsupported_prefix(mock_warning):
    result = resolve_data_link(
        "10.99999", "https://example.com/data/file.csv", "doi_dir"
    )

    assert result == []
    mock_warning.assert_called_once()
    assert "10.99999" in mock_warning.call_args.args[0]


# --- echo_resolved_data_links ---


@patch("click.echo")
def test_echo_resolved_data_links_single_file(mock_echo):
    resolved = [("doi_dir/file.csv", "https://s3.wsl.ch/envidat/file.csv", 1024 * 1024)]

    echo_resolved_data_links("10.16904/abc", resolved)

    summary = mock_echo.call_args_list[1].args[0]
    file_line = mock_echo.call_args_list[2].args[0]
    assert "1 data object(s)" in summary
    assert "10.16904/abc" in summary
    assert "1.0 MB" in summary
    assert "  (1.0 MB)  doi_dir/file.csv" == file_line


@patch("click.echo")
def test_echo_resolved_data_links_multiple_files(mock_echo):
    resolved = [
        ("doi_dir/file1.csv", "https://s3.wsl.ch/file1.csv", 512 * 1024 * 1024),
        ("doi_dir/file2.nc", "https://s3.wsl.ch/file2.nc", 512 * 1024 * 1024),
    ]

    echo_resolved_data_links("10.16904/abc", resolved)

    summary = mock_echo.call_args_list[1].args[0]
    file_line_1 = mock_echo.call_args_list[2].args[0]
    file_line_2 = mock_echo.call_args_list[3].args[0]
    assert "2 data object(s)" in summary
    assert "1.0 GB" in summary  # total
    assert "  (512.0 MB)  doi_dir/file1.csv" == file_line_1
    assert "  (512.0 MB)  doi_dir/file2.nc" == file_line_2


@patch("click.echo")
def test_echo_resolved_data_links_unknown_size(mock_echo):
    resolved = [("doi_dir/file.csv", "https://s3.wsl.ch/file.csv", 0)]

    echo_resolved_data_links("10.16904/abc", resolved)

    summary = mock_echo.call_args_list[1].args[0]
    file_line = mock_echo.call_args_list[2].args[0]
    assert "size unknown" in summary
    assert "  (size unknown)  doi_dir/file.csv" == file_line


@patch("click.echo")
def test_echo_resolved_data_links_blank_line_first(mock_echo):
    resolved = [("doi_dir/file.csv", "https://s3.wsl.ch/file.csv", 1024)]

    echo_resolved_data_links("10.16904/abc", resolved)

    assert mock_echo.call_args_list[0].args[0] == ""


# --- upload_data_link ---


@patch("datacite_websnap.exporter.stream_url_to_s3")
@patch("click.echo")
def test_upload_data_link(mock_echo, mock_stream):
    mock_s3 = MagicMock()

    upload_data_link(
        "doi_dir/file.csv",
        "https://example.com/file.csv",
        mock_s3,
        "my-bucket",
        show_upload_progress=True,
    )

    mock_echo.assert_called_once()
    assert "my-bucket" in mock_echo.call_args.args[0]
    mock_stream.assert_called_once_with(
        url="https://example.com/file.csv",
        bucket="my-bucket",
        key="doi_dir/file.csv",
        s3_client=mock_s3,
        show_upload_progress=True,
    )


# --- s3_key_exists ---


def test_s3_key_exists_returns_true():
    mock_s3 = MagicMock()
    assert s3_key_exists(mock_s3, "my-bucket", "prefix/file.xml") is True
    mock_s3.head_object.assert_called_once_with(
        Bucket="my-bucket", Key="prefix/file.xml"
    )


def test_s3_key_exists_returns_false_on_404():
    mock_s3 = MagicMock()
    mock_s3.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
    )
    assert s3_key_exists(mock_s3, "my-bucket", "prefix/missing.xml") is False


def test_s3_key_exists_raises_on_other_client_error():
    mock_s3 = MagicMock()
    mock_s3.head_object.side_effect = ClientError(
        {"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadObject"
    )
    with pytest.raises(CustomClickException, match="Failed to check key"):
        s3_key_exists(mock_s3, "my-bucket", "prefix/file.xml")


# --- write_local_file_data_links ---


@patch("datacite_websnap.exporter.CustomWarning")
def test_write_local_file_data_links_envicloud_url_warns(mock_warning):
    write_local_file_data_links(
        url="https://envicloud.wsl.ch/#/?bucket=test",
        doi_directory="/tmp/doi",
        doi_prefix="10.16904",
    )
    mock_warning.assert_called_once()
    assert "envicloud.wsl.ch" in mock_warning.call_args.args[0]


@patch("datacite_websnap.exporter.write_local_file")
@patch("datacite_websnap.exporter.get_url_content", return_value=b"data")
def test_write_local_file_data_links_regular_url_writes_file(mock_content, mock_write):
    write_local_file_data_links(
        url="https://example.com/data/file.csv",
        doi_directory="/tmp/doi",
        doi_prefix="10.16904",
    )
    mock_write.assert_called_once_with(
        content_bytes=b"data",
        filename="file.csv",
        directory_path="/tmp/doi",
    )


@patch("datacite_websnap.exporter.CustomWarning")
def test_write_local_file_data_links_unsupported_prefix_warns(mock_warning):
    write_local_file_data_links(
        url="https://example.com/data/file.csv",
        doi_directory="/tmp/doi",
        doi_prefix="10.99999",
    )
    mock_warning.assert_called_once()
    assert "10.99999" in mock_warning.call_args.args[0]


@patch("datacite_websnap.exporter.CustomWarning")
@patch("datacite_websnap.exporter.get_url_content", return_value=b"data")
def test_write_local_file_data_links_empty_filename_warns(mock_content, mock_warning):
    write_local_file_data_links(
        url="https://example.com/",
        doi_directory="/tmp/doi",
        doi_prefix="10.16904",
    )
    mock_warning.assert_called_once()
    assert "https://example.com/" in mock_warning.call_args.args[0]
