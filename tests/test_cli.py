"""Tests for src/datacite-websnap/cli.py"""

import click.testing
from unittest.mock import patch, MagicMock
import pytest

from datacite_websnap.cli import cli, datacite_bulk_export, _write_local_file_data_links
from datacite_websnap.logger import CustomClickException


def test_export_command_help():
    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["bulk-export", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "--client-id" in result.output


def test_bulk_export_command_local_success(tmp_path):
    runner = click.testing.CliRunner()

    mock_xml_list = [
        {"10.123/abc": "PGhlbGxvPjwvaGVsbG8+"}  # Base64 for <hello>
    ]

    with (
        patch(
            "datacite_websnap.cli.get_datacite_list_dois_xml",
            return_value=mock_xml_list,
        ),
        patch("datacite_websnap.cli.get_datacite_client"),
        patch("datacite_websnap.cli.write_local_file") as mock_write_file,
        patch("datacite_websnap.cli.CustomEcho"),
        patch("datacite_websnap.cli.decode_base64_xml", return_value=b"<hello>"),
        patch(
            "datacite_websnap.cli.format_xml_file_name", return_value="10.123_abc.xml"
        ),
    ):
        result = runner.invoke(
            cli,
            [
                "bulk-export",
                "--client-id",
                "test-client",
                "--destination",
                "local",
                "--directory-path",
                str(tmp_path),
            ],
        )

    assert result.exit_code == 0
    mock_write_file.assert_called_once()


@patch("datacite_websnap.cli.create_s3_client")
@patch("datacite_websnap.cli.s3_client_put_object")
@patch("datacite_websnap.cli.get_datacite_list_dois_xml")
def test_bulk_export_s3_logic_flow(mock_get_xml, mock_put_obj, mock_create_s3):
    """
    Tests the creation of the S3 client and the subsequent put_object call.
    """
    runner = click.testing.CliRunner()

    # Mock data: One record to process
    mock_get_xml.return_value = [{"doi/123": "base64str"}]

    # Mock the client instance
    mock_s3_instance = MagicMock()
    mock_create_s3.return_value = mock_s3_instance

    # We need to mock these to prevent the loop from crashing
    with (
        patch("datacite_websnap.cli.decode_base64_xml", return_value=b"<xml/>"),
        patch(
            "datacite_websnap.cli.format_xml_file_name", return_value="formatted.xml"
        ),
        patch("datacite_websnap.cli.get_datacite_client"),
        patch("datacite_websnap.cli.validate_at_least_one_query_param"),
        patch("datacite_websnap.cli.validate_bucket"),
        patch("datacite_websnap.cli.validate_key_prefix"),
        patch("datacite_websnap.cli.validate_endpoint_url"),
        patch("datacite_websnap.cli.validate_directory_path"),
    ):
        runner.invoke(
            cli,
            [
                "bulk-export",
                "--client-id",
                "test.id",
                "--destination",
                "S3",
                "--bucket",
                "my-bucket",
                "--endpoint-url",
                "https://s3.com",
                "--profile-name",
                "my-profile",
                "--file-logs",
            ],
        )

    mock_create_s3.assert_called_once_with("https://s3.com", "my-bucket", "my-profile")

    # Note: Ensure the argument names (client, body, etc.) match your function signature
    mock_put_obj.assert_called_once_with(
        client=mock_s3_instance, body=b"<xml/>", bucket="my-bucket", key="formatted.xml"
    )


@patch("datacite_websnap.cli.create_s3_client")
def test_s3_client_not_created_when_local(mock_create_s3):
    """
    Ensures S3 client logic is skipped if destination is local.
    """
    runner = click.testing.CliRunner()

    with (
        patch("datacite_websnap.cli.get_datacite_list_dois_xml", return_value=[]),
        patch("datacite_websnap.cli.get_datacite_client"),
        patch("datacite_websnap.cli.validate_at_least_one_query_param"),
        patch("datacite_websnap.cli.validate_directory_path"),
        patch("datacite_websnap.cli.validate_bucket"),
        patch("datacite_websnap.cli.validate_key_prefix"),
        patch("datacite_websnap.cli.validate_endpoint_url"),
    ):
        runner.invoke(
            cli, ["bulk-export", "--client-id", "test.id", "--destination", "local"]
        )

    # Assert create_s3_client was never called
    mock_create_s3.assert_not_called()


def test_export_command_error_early_exit(tmp_path):
    runner = click.testing.CliRunner()

    mock_xml_list = [
        {"10.123/abc": "invalid==="}  # Intentionally trigger decode error
    ]

    with (
        patch(
            "datacite_websnap.cli.get_datacite_list_dois_xml",
            return_value=mock_xml_list,
        ),
        patch("datacite_websnap.cli.get_datacite_client"),
        patch("datacite_websnap.cli.CustomWarning") as mock_warning,
        patch("datacite_websnap.cli.CustomEcho"),
        patch(
            "datacite_websnap.cli.decode_base64_xml",
            side_effect=CustomClickException("Decode failed"),
        ),
    ):
        result = runner.invoke(
            cli,
            [
                "bulk-export",
                "--client-id",
                "test-client",
                "--destination",
                "local",
                "--directory-path",
                str(tmp_path),
                "--file-logs",
                "--early-exit",
            ],
        )

    assert result.exit_code != 0
    mock_warning.assert_not_called()


def test_bulk_export_command_error_continue(tmp_path):
    runner = click.testing.CliRunner()

    mock_xml_list = [
        {"10.123/abc": "invalid==="}  # Intentionally trigger decode error
    ]

    with (
        patch(
            "datacite_websnap.cli.get_datacite_list_dois_xml",
            return_value=mock_xml_list,
        ),
        patch("datacite_websnap.cli.get_datacite_client"),
        patch("datacite_websnap.cli.CustomWarning") as mock_warning,
        patch("datacite_websnap.cli.CustomEcho"),
        patch(
            "datacite_websnap.cli.decode_base64_xml",
            side_effect=CustomClickException("Decode failed"),
        ),
    ):
        result = runner.invoke(
            cli,
            [
                "bulk-export",
                "--client-id",
                "test-client",
                "--destination",
                "local",
                "--directory-path",
                str(tmp_path),
                "--file-logs",
            ],
        )

    assert result.exit_code == 0
    mock_warning.assert_called_once()


def test_write_local_file_data_links_success(tmp_path):
    with patch("datacite_websnap.cli.get_url_content", return_value=b"data") as mock_get:
        with patch("datacite_websnap.cli.write_local_file") as mock_write:
            _write_local_file_data_links("https://example.com/files/data.csv", str(tmp_path))
            mock_get.assert_called_once_with("https://example.com/files/data.csv")
            mock_write.assert_called_once_with(
                content_bytes=b"data",
                filename="data.csv",
                directory_path=str(tmp_path),
            )


def test_write_local_file_data_links_no_content(tmp_path):
    with patch("datacite_websnap.cli.get_url_content", return_value=None):
        with patch("datacite_websnap.cli.write_local_file") as mock_write:
            _write_local_file_data_links("https://example.com/files/data.csv", str(tmp_path))
            mock_write.assert_not_called()


def test_bulk_export_unsupported_destination():
    """case _ in the match block raises CustomClickException for unknown destinations."""
    mock_xml_list = [{"10.123/abc": "PGhlbGxvPjwvaGVsbG8+"}]

    with (
        patch(
            "datacite_websnap.cli.get_datacite_list_dois_xml",
            return_value=mock_xml_list,
        ),
        patch("datacite_websnap.cli.get_datacite_client"),
        patch("datacite_websnap.cli.validate_at_least_one_query_param"),
        patch("datacite_websnap.cli.validate_key_prefix"),
        patch("datacite_websnap.cli.validate_bucket"),
        patch("datacite_websnap.cli.validate_endpoint_url"),
        patch("datacite_websnap.cli.validate_directory_path"),
        patch("datacite_websnap.cli.create_s3_client"),
        patch("datacite_websnap.cli.decode_base64_xml", return_value=b"<hello>"),
        patch("datacite_websnap.cli.format_xml_file_name", return_value="file.xml"),
        patch("datacite_websnap.cli.CustomEcho"),
    ):
        with pytest.raises(CustomClickException, match="Unsupported destination"):
            datacite_bulk_export.callback(
                destination="ftp",
                profile_name=None,
                endpoint_url=None,
                bucket=None,
                key_prefix=None,
                directory_path=None,
                file_logs=False,
                log_level="INFO",
                api_url="https://api.datacite.org",
                doi_prefix=(),
                client_id="test-client",
                early_exit=True,
                page_size=250,
            )
