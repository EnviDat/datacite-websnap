"""Tests for src/datacite-websnap/cli.py"""

import click.testing
from unittest.mock import patch, MagicMock

from datacite_websnap.cli import cli
from datacite_websnap.logger import CustomClickException


def test_export_command_help():
    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["export", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "--client-id" in result.output


def test_export_command_s3_success():
    runner = click.testing.CliRunner()

    mock_xml_list = [
        {"10.123/abc": "PGhlbGxvPjwvaGVsbG8+"}  # Base64 for <hello>
    ]

    with (
        patch(
            "datacite_websnap.cli.get_datacite_list_dois_xml",
            return_value=mock_xml_list,
        ),
        patch("datacite_websnap.cli.validate_s3_config"),
        patch("datacite_websnap.cli.create_s3_client", return_value=MagicMock()),
        patch("datacite_websnap.cli.get_datacite_client"),
        patch("datacite_websnap.cli.s3_client_put_object"),
        patch("datacite_websnap.cli.CustomEcho"),
        patch("datacite_websnap.cli.validate_single_string_key_value"),
        patch("datacite_websnap.cli.decode_base64_xml", return_value=b"<hello>"),
        patch(
            "datacite_websnap.cli.format_xml_file_name", return_value="10.123_abc.xml"
        ),
    ):
        result = runner.invoke(
            cli,
            [
                "export",
                "--client-id",
                "test-client",
                "--bucket",
                "test-bucket",
                "--file-logs",
            ],
        )

    assert result.exit_code == 0


def test_export_command_local_success(tmp_path):
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
        patch("datacite_websnap.cli.validate_single_string_key_value"),
        patch("datacite_websnap.cli.decode_base64_xml", return_value=b"<hello>"),
        patch(
            "datacite_websnap.cli.format_xml_file_name", return_value="10.123_abc.xml"
        ),
    ):
        result = runner.invoke(
            cli,
            [
                "export",
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
    mock_write_file.assert_called_once()


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
            "datacite_websnap.cli.validate_single_string_key_value",
            side_effect=CustomClickException("Validation failed"),
        ),
    ):
        result = runner.invoke(
            cli,
            [
                "export",
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


def test_export_command_error_continue(tmp_path):
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
            "datacite_websnap.cli.validate_single_string_key_value",
            side_effect=CustomClickException("Validation failed"),
        ),
    ):
        result = runner.invoke(
            cli,
            [
                "export",
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
