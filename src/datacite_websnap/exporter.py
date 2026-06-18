"""
Process and export DataCite XML metadata records.
"""

import base64
import hashlib

import binascii
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import click
import requests
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    BotoCoreError,
    NoCredentialsError,
    EndpointConnectionError,
)
import boto3

from .http_utils import get_url_content, get_url_content_length
from .logger import CustomClickException, custom_echo, custom_warning
from .config import TIMEOUT
from .repositories.envidat import get_envicloud_objects


def decode_base64_xml(encoded_xml: str) -> bytes:
    """
    Decodes a Base64-encoded XML string and returns it as a bytes object.

    Args:
        encoded_xml: Base64-encoded XML string.
    """
    try:
        decoded = base64.b64decode(encoded_xml)
    except binascii.Error:
        raise CustomClickException("binascii Error: Unable to decode XML")
    except Exception as err:
        raise CustomClickException(f"Unexpected error: {err}")

    try:
        ET.fromstring(decoded)
    except ET.ParseError as err:
        raise CustomClickException(f"Invalid XML structure: {err}")

    return decoded


def format_doi_stem(doi: str) -> str:
    """
    Return formatted "doi" value: "/" and ":" replaced with "_"

    Args:
        doi: "doi" string, example "10.16904/envidat.31"
    """
    return doi.replace("/", "_").replace(":", "_")


def format_xml_file_name(doi: str, key_prefix: str | None = None) -> str:
    """
    Format "doi" value into an XML filename.
    "/" and ":" replaced with "_" and ".xml" appended to the filename.

    Also supports formatting a "doi" value with an S3 key prefix.

    Example input: "10.16904/envidat.31"
    Example output: "10.16904_envidat.31.xml"

    Args:
        doi: "doi" string, example "10.16904/envidat.31"
        key_prefix: Optional key prefix for objects in S3 bucket.
    """
    doi_format = format_doi_stem(doi)

    if not key_prefix:
        return f"{doi_format}.xml"

    return f"{key_prefix}/{doi_format}.xml"


def format_json_file_name(xml_file_name: str) -> str:
    """
    Format xml_filename into a JSON filename.

    Args:
        xml_file_name: XML file name assigned from formatted DOI.
    """
    return Path(xml_file_name).with_suffix(".json").as_posix()


def create_s3_client(
    endpoint_url: str, bucket: str, profile_name: str | None = None
) -> Any:
    """
    Returns a validated Boto3 S3 client created using a shared AWS credentials file.

    To learn more see
    https://docs.aws.amazon.com/boto3/latest/guide/credentials.html#shared-credentials-file

    Args:
        endpoint_url: The complete URL to use for the constructed S3 client.
        bucket: Name of S3 bucket that DataCite XML records (as S3 objects) will be
                written in. Must have access to bucket with passed S3 credentials.
        profile_name: The name of a profile to use for S3 credentials file.
                      If not given, then the default profile is used.

    Raises:
        CustomClickException: If the client could not be created or accessed.
    """
    try:
        session = (
            boto3.Session(profile_name=profile_name)
            if profile_name
            else boto3.Session()
        )

        client = session.client(
            service_name="s3",
            endpoint_url=endpoint_url,
            config=Config(
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                connect_timeout=5,
                read_timeout=TIMEOUT,
                retries={"max_attempts": 3},
                max_pool_connections=50,
            ),
        )

    except (BotoCoreError, EndpointConnectionError) as e:
        raise CustomClickException(f"Failed to create S3 client: {e}")

    try:
        # Validate credentials, endpoint and access to an existing bucket
        client.head_bucket(Bucket=bucket)
    except NoCredentialsError as e:
        raise CustomClickException(f"S3 credentials are missing: {e}")
    except (ClientError, EndpointConnectionError) as e:
        raise CustomClickException(
            f"S3 credentials, endpoint and/or bucket are invalid "
            f"(or credentials are not valid for bucket): {e}"
        )

    return client


def s3_client_put_object(client: Any, body: bytes, bucket: str, key: str) -> None:
    """
    Copy string as an S3 object to a S3 bucket.

    NOTE: This function will overwrite objects with the same key names!

    Args:
        client: configured Boto3 S3 client
        body: bytes object that will be written as an S3 object's data
        bucket: name of bucket that object should be written in
        key: name (or path) of the object in the S3 bucket
    """
    err_msg = f"Failed to export key {key}: "

    try:
        response_s3 = client.put_object(Body=body, Bucket=bucket, Key=key)
    except ClientError as err:
        raise CustomClickException(f"{err_msg}boto3 ClientError: {err}")
    except Exception as err:
        raise CustomClickException(f"{err_msg}Unexpected error: {err}")

    status_code = response_s3.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status_code is None:
        raise CustomClickException(
            f"{err_msg}Missing ResponseMetadata in S3 response for key '{key}'"
        )

    if status_code != 200:
        raise CustomClickException(
            f"{err_msg}S3 client returned unexpected status code "
            f"{status_code} for key '{key}'"
        )

    custom_echo(
        f"Successfully exported to bucket '{bucket}' DataCite DOI record: {key}"
    )


def write_local_file(
    content_bytes: bytes, filename: str, directory_path: str | None = None
) -> None:
    """
    Write a bytes object to a local file.

    Args:
        content_bytes: bytes object that will be written to a local file
        filename: name of file to write, be sure to include desired extension
        directory_path: path to directory to write the file in
    """
    try:
        if directory_path:
            file_path = Path(directory_path) / filename
        else:
            file_path = Path(filename)

        with open(file_path, "wb") as f:
            f.write(content_bytes)

        posix_file_path = file_path.as_posix()
        custom_echo(f"Wrote local file: {posix_file_path}")

    except IOError as io_err:
        raise CustomClickException(f"IOError: {io_err}")

    except Exception as err:
        raise CustomClickException(f"Unexpected error: {err}")


def _extract_filename(url: str) -> str:
    """Extract filename from url.
    Returns parent part of path for urls that end in "/content".

     Args:
        url: url that should have filename extracted

    Returns:
        The extracted filename, or a 16-character SHA-1 hash of the
        url if a filename cannot be determined.
    """

    path_obj = Path(urlparse(url).path)

    if path_obj.name == "content":
        # URL ends with "/content" -> the real filename is assumed to be one level up
        filename = path_obj.parent.name
    else:
        # Normal case -> last path segment is the filename
        filename = path_obj.name

    if not filename:
        url_hash = hashlib.sha1(url.encode()).hexdigest()[:16]
        filename = f"{url_hash}"

    return filename


def write_local_file_data_links(url: str, doi_directory: str, doi_prefix: str) -> None:
    """
    Write a bytes object to a local file.
    The content in the local file corresponds a data file resource
    passed as a URL in the DOI metadata.

    Currently only supports writing EnviDat files (that are not in envicloud).

    Args:
        url: URL that leads to the data content
        doi_directory: local path to directory to write the file in
        doi_prefix: prefix of the DOI
    """
    match doi_prefix:
        case "10.16904":  # EnviDat DOI prefix
            if url.startswith("https://envicloud.wsl.ch/#/?bucket="):
                custom_warning(
                    f"Failed to write '{url}' locally. CLI "
                    f"does not support writing local data files for files "
                    f"that are hosted at 'https://envicloud.wsl.ch'"
                )

            elif content := get_url_content(url):
                file_name = Path(urlparse(url).path).name
                if file_name:
                    write_local_file(
                        content_bytes=content,
                        filename=file_name,
                        directory_path=doi_directory,
                    )
                else:
                    # Logs warning for EnviDat filenames that could not be extracted
                    #  from url (rather than assigning a random string as filename)
                    custom_warning(f"Could not determine filename from URL: '{url}'")

        case "10.24435":  # Materials Cloud DOI prefix
            if content := get_url_content(url):
                write_local_file(
                    content_bytes=content,
                    filename=_extract_filename(url),
                    directory_path=doi_directory,
                )

        case _:
            custom_warning(
                f"CLI does not support writing local data files for DOI "
                f"prefix: {doi_prefix}. Failed to write file '{url}' locally."
            )


class _UploadProgress:
    def __init__(self, total_bytes: int = 0) -> None:
        self._transferred = 0
        self._total_bytes = total_bytes
        self._use_mb = total_bytes >= 1024**2

    def _fmt(self, size_bytes: int) -> str:
        if self._use_mb:
            return f"{size_bytes / 1024**2:.1f} MB"
        return f"{size_bytes / 1024:.1f} KB"

    def __call__(self, bytes_transferred: int) -> None:
        self._transferred += bytes_transferred
        if self._total_bytes:
            click.echo(
                f"\r  Progress: {self._fmt(self._transferred)} / {self._fmt(self._total_bytes)}",
                nl=False,
            )
        else:
            click.echo(f"\r  Progress: {self._fmt(self._transferred)}", nl=False)


def stream_url_to_s3(
    url: str,
    bucket: str,
    key: str,
    s3_client: Any,
    show_upload_progress: bool = False,
) -> None:
    """
    Streams content from a URL directly to an S3 bucket without loading into memory.

    Args:
        url: URL of the resource to stream.
        bucket: S3 bucket name.
        key: S3 object key.
        s3_client: configured Boto3 S3 client.
        show_upload_progress: if True display an upload progress bar,
                           default value is False
    """
    try:
        with requests.get(url, stream=True, timeout=(10, 60)) as response:
            response.raise_for_status()
            response.raw.decode_content = True

            total_bytes = int(response.headers.get("Content-Length", 0))
            callback = _UploadProgress(total_bytes) if show_upload_progress else None

            s3_client.upload_fileobj(
                Fileobj=response.raw,
                Bucket=bucket,
                Key=key,
                Callback=callback,
            )

            if show_upload_progress:
                click.echo()  # terminate progress line

            custom_echo(
                f"Successfully exported to bucket '{bucket}' data object: {key}"
            )

    except requests.exceptions.Timeout:
        custom_warning(f"Request timed out fetching URL: '{url}'")
    except requests.exceptions.HTTPError as err:
        custom_warning(f"HTTP error fetching URL '{url}': {err}")
    except requests.exceptions.RequestException as err:
        custom_warning(f"Error fetching URL '{url}': {err}")
    except (BotoCoreError, ClientError) as err:
        custom_warning(f"Unexpected error streaming '{url}' to S3: {err}")


def resolve_data_link(
    doi_prefix: str, url: str, doi_s3_dir: str
) -> list[tuple[str, str, int]]:
    """
    Resolve a data link URL to upload ready (s3_key, download_url, size_bytes) tuples.
    Returns an empty list if the prefix is unsupported or the URL cannot be resolved.

    Args:
        doi_prefix: prefix of the DOI
        url: URL that leads to the data content
        doi_s3_dir: S3 directory prefix for the DOI
    """
    match doi_prefix:
        case "10.16904":  # EnviDat DOI prefix
            if url.startswith("https://envicloud.wsl.ch/#/?bucket="):
                envicloud_objects = get_envicloud_objects(url)
                if not envicloud_objects:
                    return []
                return [
                    (f"{doi_s3_dir}/{obj_key}", obj_url, size)
                    for obj_key, obj_url, size in envicloud_objects
                ]
            else:
                size = get_url_content_length(url)
                file_name = Path(urlparse(url).path).name
                if file_name:
                    return [(f"{doi_s3_dir}/{file_name}", url, size)]
                return []
        case _:
            custom_warning(
                f"CLI does not support exporting S3 data files for "
                f"DOI prefix: {doi_prefix}."
            )
            return []


def format_size(size_bytes: int) -> str:
    if not size_bytes:
        return "size unknown"
    if size_bytes >= 1024**3:
        return f"{size_bytes / 1024**3:.1f} GB"
    if size_bytes >= 1024**2:
        return f"{size_bytes / 1024**2:.1f} MB"
    return f"{size_bytes / 1024:.1f} KB"


def echo_resolved_data_links(
    doi: str, resolved: list[tuple[str, str, int]], fg_color: str = "cyan"
) -> None:
    """
    Log a pre-flight summary of resolved data files pending upload.

    Args:
        doi: DataCite DOI
        resolved: list of (s3_key, download_url, size_bytes) tuples
        fg_color: color for fg for informational message, default color is cyan
    """
    total_size = sum(size for _, _, size in resolved)
    click.echo("")

    click.echo(
        click.style(
            f"Found {len(resolved)} data object(s) "
            f"for DataCite DOI '{doi}' "
            f"to upload ({format_size(total_size)} total):",
            fg=fg_color,
            bold=True,
        )
    )
    for s3_key, _, size in resolved:
        click.echo(f"  ({format_size(size)})  {s3_key}")


def upload_data_link(
    s3_key: str,
    download_url: str,
    s3_client: Any,
    bucket: str,
    show_upload_progress: bool = False,
) -> None:
    """
    Upload a single resolved data file from download_url to S3.

    Args:
        s3_key: S3 object key to write to
        download_url: URL to stream content from
        s3_client: configured Boto3 S3 client
        bucket: S3 bucket name
        show_upload_progress: if True display an upload progress bar and upload message,
                              default value is False
    """
    if show_upload_progress:
        click.echo(f"Uploading to bucket '{bucket}': {download_url}")

    stream_url_to_s3(
        url=download_url,
        bucket=bucket,
        key=s3_key,
        s3_client=s3_client,
        show_upload_progress=show_upload_progress,
    )


def s3_key_exists(s3_client: Any, bucket: str, s3_key: str) -> bool:
    """
    Return True if key exists in bucket. Else return False.
    Raises CustomException if failed to check key.

    Args:
    s3_client: configured Boto3 S3 client
    bucket: S3 bucket name
    s3_key: S3 object key to check
    """
    try:
        s3_client.head_object(Bucket=bucket, Key=s3_key)
        return True
    except ClientError as err:
        if err.response["Error"]["Code"] == "404":
            return False
        raise CustomClickException(f"Failed to check key '{s3_key}': {err}")
