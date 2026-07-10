"""Tests for src/datacite-websnap/cli.py"""

import click.testing
from unittest.mock import patch, MagicMock
import pytest

from datacite_websnap.cli import (
    cli,
    datacite_bulk_export,
    _export_doi_s3,
    _export_doi_local,
    _upload_data_links_s3,
)
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
        patch("datacite_websnap.cli.custom_echo"),
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

    with (
        patch("datacite_websnap.cli.decode_base64_xml", return_value=b"<xml/>"),
        patch(
            "datacite_websnap.cli.format_xml_file_name", return_value="formatted.xml"
        ),
        patch("datacite_websnap.cli.get_datacite_client"),
    ):
        result = runner.invoke(
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

    assert result.exit_code == 0
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
        patch("datacite_websnap.cli.custom_warning") as mock_warning,
        patch("datacite_websnap.cli.custom_echo"),
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
        patch("datacite_websnap.cli.custom_warning") as mock_warning,
        patch("datacite_websnap.cli.custom_echo"),
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
        patch("datacite_websnap.cli.custom_echo"),
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


# --- _export_doi_local ---


def test_export_doi_local_writes_xml_and_json(tmp_path):
    _export_doi_local(
        doi_bare="10.123/test",
        doi_prefix="10.123",
        xml_decoded=b"<xml/>",
        json_resp={"key": "value"},
        data_links=[],
        directory_path=str(tmp_path),
        url="https://example.com/10.123/test",
    )
    doi_dir = tmp_path / "10.123_test"
    assert (doi_dir / "10.123_test.xml").read_bytes() == b"<xml/>"
    assert b'"key": "value"' in (doi_dir / "10.123_test.json").read_bytes()


@patch("datacite_websnap.cli.write_local_file_data_links")
def test_export_doi_local_calls_data_links(mock_write_links, tmp_path):
    _export_doi_local(
        doi_bare="10.123/test",
        doi_prefix="10.123",
        xml_decoded=b"<xml/>",
        json_resp={},
        data_links=["https://example.com/file.csv"],
        directory_path=str(tmp_path),
        url="https://example.com/10.123/test",
    )
    mock_write_links.assert_called_once()
    assert mock_write_links.call_args.args[0] == "https://example.com/file.csv"


# --- _export_doi_s3 ---


@patch("datacite_websnap.cli._upload_data_links_s3")
@patch("datacite_websnap.cli.s3_client_put_object")
@patch("datacite_websnap.cli.s3_key_exists", return_value=False)
def test_export_doi_s3_no_existing_metadata(mock_exists, mock_put, mock_upload):
    mock_s3 = MagicMock()
    _export_doi_s3(
        doi_bare="10.123/test",
        doi_prefix="10.123",
        xml_decoded=b"<xml/>",
        json_resp={"key": "value"},
        data_links=[],
        s3_client=mock_s3,
        bucket="my-bucket",
        key_prefix="prefix",
    )
    assert mock_put.call_count == 2
    keys = [c.kwargs["key"] for c in mock_put.call_args_list]
    assert any(k.endswith(".xml") for k in keys)
    assert any(k.endswith(".json") for k in keys)
    mock_upload.assert_called_once()


@patch("datacite_websnap.cli._upload_data_links_s3")
@patch("datacite_websnap.cli.s3_client_put_object")
@patch("datacite_websnap.cli.s3_key_exists", return_value=True)
def test_export_doi_s3_existing_metadata_overwrite_yes(
    mock_exists, mock_put, mock_upload
):
    runner = click.testing.CliRunner()
    mock_s3 = MagicMock()
    with runner.isolated_filesystem():
        with patch("datacite_websnap.cli.click.confirm", return_value=True):
            _export_doi_s3(
                doi_bare="10.123/test",
                doi_prefix="10.123",
                xml_decoded=b"<xml/>",
                json_resp={},
                data_links=[],
                s3_client=mock_s3,
                bucket="my-bucket",
                key_prefix=None,
            )
    assert mock_put.call_count == 2


@patch("datacite_websnap.cli._upload_data_links_s3")
@patch("datacite_websnap.cli.s3_client_put_object")
@patch("datacite_websnap.cli.s3_key_exists", return_value=True)
def test_export_doi_s3_existing_metadata_overwrite_no(
    mock_exists, mock_put, mock_upload
):
    with patch("datacite_websnap.cli.click.confirm", return_value=False):
        _export_doi_s3(
            doi_bare="10.123/test",
            doi_prefix="10.123",
            xml_decoded=b"<xml/>",
            json_resp={},
            data_links=[],
            s3_client=MagicMock(),
            bucket="my-bucket",
            key_prefix=None,
        )
    mock_put.assert_not_called()
    mock_upload.assert_called_once()


# --- _upload_data_links_s3 ---


@patch("datacite_websnap.cli.resolve_data_link", return_value=[])
def test_upload_data_links_s3_no_resolved_returns_early(mock_resolve):
    mock_s3 = MagicMock()
    _upload_data_links_s3(
        "10.123/test", "10.123", ["https://example.com/f.csv"], "dir", mock_s3, "bucket"
    )
    mock_resolve.assert_called_once()


@patch("datacite_websnap.cli.upload_data_link")
@patch("datacite_websnap.cli.s3_key_exists", return_value=False)
@patch(
    "datacite_websnap.cli.resolve_data_link",
    return_value=[("dir/f.csv", "https://example.com/f.csv", 100)],
)
def test_upload_data_links_s3_new_data_confirm_yes(
    mock_resolve, mock_exists, mock_upload
):
    with patch("datacite_websnap.cli.click.confirm", return_value=True):
        _upload_data_links_s3(
            "10.123/test",
            "10.123",
            ["https://example.com/f.csv"],
            "dir",
            MagicMock(),
            "bucket",
        )
    mock_upload.assert_called_once()


@patch("datacite_websnap.cli.upload_data_link")
@patch("datacite_websnap.cli.s3_key_exists", return_value=False)
@patch(
    "datacite_websnap.cli.resolve_data_link",
    return_value=[("dir/f.csv", "https://example.com/f.csv", 100)],
)
def test_upload_data_links_s3_new_data_confirm_no(
    mock_resolve, mock_exists, mock_upload
):
    with patch("datacite_websnap.cli.click.confirm", return_value=False):
        _upload_data_links_s3(
            "10.123/test",
            "10.123",
            ["https://example.com/f.csv"],
            "dir",
            MagicMock(),
            "bucket",
        )
    mock_upload.assert_not_called()


@patch("datacite_websnap.cli.upload_data_link")
@patch("datacite_websnap.cli.s3_key_exists", return_value=True)
@patch(
    "datacite_websnap.cli.resolve_data_link",
    return_value=[("dir/f.csv", "https://example.com/f.csv", 100)],
)
def test_upload_data_links_s3_existing_data_overwrite_yes(
    mock_resolve, mock_exists, mock_upload
):
    with patch("datacite_websnap.cli.click.confirm", return_value=True):
        _upload_data_links_s3(
            "10.123/test",
            "10.123",
            ["https://example.com/f.csv"],
            "dir",
            MagicMock(),
            "bucket",
        )
    mock_upload.assert_called_once()


@patch("datacite_websnap.cli.upload_data_link")
@patch("datacite_websnap.cli.s3_key_exists", return_value=True)
@patch(
    "datacite_websnap.cli.resolve_data_link",
    return_value=[("dir/f.csv", "https://example.com/f.csv", 100)],
)
def test_upload_data_links_s3_existing_data_overwrite_no(
    mock_resolve, mock_exists, mock_upload
):
    with patch("datacite_websnap.cli.click.confirm", return_value=False):
        _upload_data_links_s3(
            "10.123/test",
            "10.123",
            ["https://example.com/f.csv"],
            "dir",
            MagicMock(),
            "bucket",
        )
    mock_upload.assert_not_called()


@patch("datacite_websnap.cli.upload_data_link")
@patch("datacite_websnap.cli.s3_key_exists", return_value=False)
@patch("datacite_websnap.cli.resolve_data_link")
def test_upload_data_links_s3_parallel_path_uploads_all(
    mock_resolve, mock_exists, mock_upload
):
    # Single URL resolves to 11 objects (e.g. an envicloud bucket with 11 files)
    items = [(f"dir/f{i}.csv", f"https://example.com/f{i}.csv", 100) for i in range(11)]
    mock_resolve.return_value = items

    with patch("datacite_websnap.cli.click.confirm", return_value=True):
        _upload_data_links_s3(
            "10.123/test",
            "10.123",
            ["https://envicloud.wsl.ch/#/?bucket=test"],
            "dir",
            MagicMock(),
            "bucket",
        )
    assert mock_upload.call_count == 11


# --- datacite_single_doi_export ---


@patch("datacite_websnap.cli._export_doi_local")
@patch("datacite_websnap.cli.validate_doi_eth_standard")
@patch("datacite_websnap.cli.decode_base64_xml", return_value=b"<xml/>")
@patch(
    "datacite_websnap.cli.get_datacite_doi",
    return_value=({"key": "val"}, "base64xml", [], "https://example.com/doi"),
)
def test_doi_export_command_local_success(
    mock_get_doi, mock_decode, mock_validate, mock_export, tmp_path
):
    runner = click.testing.CliRunner()
    result = runner.invoke(
        cli,
        [
            "doi-export",
            "--doi",
            "10.16904/envidat.31",
            "--destination",
            "local",
            "--directory-path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    mock_get_doi.assert_called_once()
    mock_validate.assert_called_once()
    mock_export.assert_called_once()


@patch("datacite_websnap.cli._export_doi_s3")
@patch("datacite_websnap.cli.create_s3_client")
@patch("datacite_websnap.cli.validate_doi_eth_standard")
@patch("datacite_websnap.cli.decode_base64_xml", return_value=b"<xml/>")
@patch(
    "datacite_websnap.cli.get_datacite_doi",
    return_value=({"key": "val"}, "base64xml", [], "https://example.com/doi"),
)
def test_doi_export_command_s3_success(
    mock_get_doi, mock_decode, mock_validate, mock_s3, mock_export
):
    runner = click.testing.CliRunner()
    result = runner.invoke(
        cli,
        [
            "doi-export",
            "--doi",
            "10.16904/envidat.31",
            "--destination",
            "S3",
            "--bucket",
            "my-bucket",
            "--endpoint-url",
            "https://s3.example.com",
        ],
    )
    assert result.exit_code == 0
    mock_export.assert_called_once()


def test_doi_export_command_invalid_doi():
    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["doi-export", "--doi", "not-a-doi"])
    assert result.exit_code != 0


@patch("datacite_websnap.cli.validate_doi_eth_standard")
@patch("datacite_websnap.cli.decode_base64_xml", return_value=b"<xml/>")
@patch(
    "datacite_websnap.cli.get_datacite_doi",
    return_value=({"key": "val"}, "base64xml", [], "https://example.com/doi"),
)
@patch(
    "datacite_websnap.cli.validate_doi",
    return_value=("10.16904/envidat.31", "10.16904"),
)
@patch("datacite_websnap.cli.validate_key_prefix")
@patch("datacite_websnap.cli.validate_bucket")
@patch("datacite_websnap.cli.validate_endpoint_url")
@patch("datacite_websnap.cli.validate_directory_path")
@patch("datacite_websnap.cli.validate_api_url")
def test_doi_export_command_unsupported_destination(
    mock_vau,
    mock_vdp,
    mock_vep,
    mock_vb,
    mock_vkp,
    mock_vd,
    mock_get_doi,
    mock_decode,
    mock_validate,
):
    from datacite_websnap.cli import datacite_single_doi_export

    with pytest.raises(CustomClickException, match="Unsupported destination"):
        datacite_single_doi_export.callback(
            doi="10.16904/envidat.31",
            destination="ftp",
            profile_name=None,
            endpoint_url=None,
            bucket=None,
            key_prefix=None,
            directory_path=None,
            file_logs=False,
            log_level="INFO",
            api_url="https://api.datacite.org",
        )
