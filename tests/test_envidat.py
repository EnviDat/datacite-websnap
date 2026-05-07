"""Tests for src/datacite-websnap/repositories/envidat.py"""

import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, BotoCoreError

from datacite_websnap.exporter import CustomClickException
from datacite_websnap.repositories.envidat import (
    parse_envicloud_url,
    create_s3_client_unsigned,
    s3_client_list_bucket_contents,
    get_envicloud_objects,
)


# --- parse_envicloud_url ---


def test_parse_envicloud_url_success():
    url = (
        "https://envicloud.wsl.ch/#/"
        "?bucket=https%3A%2F%2Fs3.wsl.ch%2Fenvidat"
        "&prefix=data%2Ffile.csv"
    )
    endpoint_url, bucket, prefix = parse_envicloud_url(url)
    assert endpoint_url == "https://s3.wsl.ch"
    assert bucket == "envidat"
    assert prefix == "data/file.csv"


def test_parse_envicloud_url_encoded_prefix():
    url = (
        "https://envicloud.wsl.ch/#/"
        "?bucket=https%3A%2F%2Fs3.wsl.ch%2Fenvidat"
        "&prefix=folder%2Fsubfolder%2Fdata.csv"
    )
    _, _, prefix = parse_envicloud_url(url)
    assert prefix == "folder/subfolder/data.csv"


def test_parse_envicloud_url_missing_bucket():
    url = "https://envicloud.wsl.ch/#/?prefix=data%2Ffile.csv"
    with patch("datacite_websnap.repositories.envidat.CustomWarning") as mock_warning:
        result = parse_envicloud_url(url)
        assert result is None
        mock_warning.assert_called_once()


def test_parse_envicloud_url_missing_prefix():
    url = "https://envicloud.wsl.ch/#/?bucket=https%3A%2F%2Fs3.wsl.ch%2Fenvidat"
    with patch("datacite_websnap.repositories.envidat.CustomWarning") as mock_warning:
        result = parse_envicloud_url(url)
        assert result is None
        mock_warning.assert_called_once()


def test_parse_envicloud_url_empty_fragment():
    url = "https://envicloud.wsl.ch/"
    with patch("datacite_websnap.repositories.envidat.CustomWarning") as mock_warning:
        result = parse_envicloud_url(url)
        assert result is None
        mock_warning.assert_called_once()


def test_parse_envicloud_url_unexpected_exception():
    url = "https://envicloud.wsl.ch/#/?bucket=https%3A%2F%2Fs3.wsl.ch%2Fenvidat&prefix=data%2Ffile.csv"
    with patch(
        "datacite_websnap.repositories.envidat.parse_qs",
        side_effect=ValueError("bad input"),
    ):
        with patch(
            "datacite_websnap.repositories.envidat.CustomWarning"
        ) as mock_warning:
            result = parse_envicloud_url(url)
            assert result is None
            mock_warning.assert_called_once()


# --- create_s3_client_unsigned ---


@patch("boto3.client")
def test_create_s3_client_unsigned_success(mock_boto3_client):
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client

    result = create_s3_client_unsigned("https://s3.wsl.ch", "envidat")

    mock_boto3_client.assert_called_once()
    mock_client.head_bucket.assert_called_once_with(Bucket="envidat")
    assert result == mock_client


@patch("boto3.client")
def test_create_s3_client_unsigned_connection_error(mock_boto3_client):
    mock_boto3_client.side_effect = BotoCoreError()

    with pytest.raises(CustomClickException, match="Failed to create S3 client"):
        create_s3_client_unsigned("http://invalid", "bucket")


@patch("boto3.client")
def test_create_s3_client_unsigned_invalid_bucket(mock_boto3_client):
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client

    error_response = {"Error": {"Code": "403", "Message": "Forbidden"}}
    mock_client.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

    with pytest.raises(CustomClickException, match="S3 endpoint URL and/or bucket"):
        create_s3_client_unsigned("https://s3.wsl.ch", "private-bucket")


# --- s3_client_list_bucket_contents ---


def test_s3_client_list_bucket_contents_single_page():
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "data/file1.csv"}, {"Key": "data/file2.nc"}],
        "IsTruncated": False,
    }

    result = s3_client_list_bucket_contents(mock_client, "bucket", "data/")

    assert len(result) == 2
    assert result[0]["Key"] == "data/file1.csv"
    mock_client.list_objects_v2.assert_called_once()


def test_s3_client_list_bucket_contents_paginated():
    mock_client = MagicMock()
    mock_client.list_objects_v2.side_effect = [
        {
            "Contents": [{"Key": "data/file1.csv"}],
            "IsTruncated": True,
            "NextContinuationToken": "token123",
        },
        {
            "Contents": [{"Key": "data/file2.nc"}],
            "IsTruncated": False,
        },
    ]

    result = s3_client_list_bucket_contents(mock_client, "bucket", "data/")

    assert len(result) == 2
    assert mock_client.list_objects_v2.call_count == 2
    second_call_kwargs = mock_client.list_objects_v2.call_args_list[1].kwargs
    assert second_call_kwargs["ContinuationToken"] == "token123"


def test_s3_client_list_bucket_contents_empty():
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {"IsTruncated": False}

    result = s3_client_list_bucket_contents(mock_client, "bucket", "data/")

    assert result == []


def test_s3_client_list_bucket_contents_client_error():
    mock_client = MagicMock()
    mock_client.list_objects_v2.side_effect = ClientError(
        {"Error": {"Code": "403", "Message": "Forbidden"}}, "ListObjectsV2"
    )

    with pytest.raises(CustomClickException, match="Failed to list objects"):
        s3_client_list_bucket_contents(mock_client, "bucket", "data/")


def test_s3_client_list_bucket_contents_unexpected_error():
    mock_client = MagicMock()
    mock_client.list_objects_v2.side_effect = Exception("something went wrong")

    with pytest.raises(CustomClickException, match="Unexpected error"):
        s3_client_list_bucket_contents(mock_client, "bucket", "data/")


# --- get_envicloud_objects ---


@patch("datacite_websnap.repositories.envidat.parse_envicloud_url")
def test_get_envicloud_objects_parse_fails(mock_parse):
    mock_parse.return_value = None

    result = get_envicloud_objects("https://envicloud.wsl.ch/#/invalid")

    assert result is None


@patch("datacite_websnap.repositories.envidat.s3_client_list_bucket_contents")
@patch("datacite_websnap.repositories.envidat.create_s3_client_unsigned")
@patch("datacite_websnap.repositories.envidat.parse_envicloud_url")
def test_get_envicloud_objects_success(mock_parse, mock_create_client, mock_list):
    mock_parse.return_value = ("https://s3.wsl.ch", "envidat", "data/")
    mock_create_client.return_value = MagicMock()
    mock_list.return_value = [
        {"Key": "data/file1.csv"},
        {"Key": "data/file2.nc"},
    ]

    result = get_envicloud_objects(
        "https://envicloud.wsl.ch/#/?bucket=...&prefix=data/"
    )

    assert result == [
        ("data/file1.csv", "https://s3.wsl.ch/envidat/data/file1.csv"),
        ("data/file2.nc", "https://s3.wsl.ch/envidat/data/file2.nc"),
    ]


@patch("datacite_websnap.repositories.envidat.s3_client_list_bucket_contents")
@patch("datacite_websnap.repositories.envidat.create_s3_client_unsigned")
@patch("datacite_websnap.repositories.envidat.parse_envicloud_url")
def test_get_envicloud_objects_filters_no_extension(
    mock_parse, mock_create_client, mock_list
):
    mock_parse.return_value = ("https://s3.wsl.ch", "envidat", "data/")
    mock_create_client.return_value = MagicMock()
    mock_list.return_value = [
        {"Key": "data/file1.csv"},
        {"Key": "data/subfolder"},
        {"Key": "data/file2.nc"},
    ]

    result = get_envicloud_objects(
        "https://envicloud.wsl.ch/#/?bucket=...&prefix=data/"
    )

    assert len(result) == 2
    assert ("data/file1.csv", "https://s3.wsl.ch/envidat/data/file1.csv") in result
    assert ("data/file2.nc", "https://s3.wsl.ch/envidat/data/file2.nc") in result
    assert ("data/subfolder", "https://s3.wsl.ch/envidat/data/subfolder") not in result


@patch("datacite_websnap.repositories.envidat.s3_client_list_bucket_contents")
@patch("datacite_websnap.repositories.envidat.create_s3_client_unsigned")
@patch("datacite_websnap.repositories.envidat.parse_envicloud_url")
def test_get_envicloud_objects_empty_bucket(mock_parse, mock_create_client, mock_list):
    mock_parse.return_value = ("https://s3.wsl.ch", "envidat", "data/")
    mock_create_client.return_value = MagicMock()
    mock_list.return_value = []

    result = get_envicloud_objects(
        "https://envicloud.wsl.ch/#/?bucket=...&prefix=data/"
    )

    assert result == []
