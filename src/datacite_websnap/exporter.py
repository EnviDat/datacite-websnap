"""
Process and export DataCite XML metadata records.
"""

import base64
from pathlib import Path
from pprint import pprint
import binascii
from typing import Any
from urllib.parse import urlparse, unquote, parse_qs

import click
import requests
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    BotoCoreError,
    NoCredentialsError,
    EndpointConnectionError,
)
import boto3

from .http_utils import get_url_content
from .logger import CustomClickException, CustomEcho, CustomWarning
from .config import TIMEOUT


def decode_base64_xml(encoded_xml: str) -> bytes:
    """
    Decodes a Base64-encoded XML string and returns it as a bytes object.

    Args:
        encoded_xml: Base64-encoded XML string.
    """
    try:
        return base64.b64decode(encoded_xml)
    except binascii.Error:
        raise CustomClickException("binascii Error: Unable to decode XML")
    except Exception as err:
        raise CustomClickException(f"Unexpected error: {err}")


def format_xml_file_name(doi: str, key_prefix: str | None = None) -> str:
    """
    Format "doi" value into an XML filename.
    "/" replaced with "_" and ".xml" appended to the filename.

    Also supports formatting a "doi" value with an S3 key prefix.

    Example input: "10.16904/envidat.31"
    Example output: "10.16904_envidat.31.xml"

    Args:
        doi: "doi" string, example "10.16904/envidat.31"
        key_prefix: Optional key prefix for objects in S3 bucket.
    """
    doi_format = doi.replace("/", "_").replace(":", "_")

    if not key_prefix:
        return f"{doi_format}.xml"

    if key_prefix.endswith("/"):
        return f"{key_prefix}{doi_format}.xml"
    else:
        return f"{key_prefix}/{doi_format}.xml"


def format_json_file_name(xml_file_name: str) -> str:
    """
    Format xml_filename into a JSON filename.

    Args:
        xml_file_name: XML file name assigned from formatted DOI.
    """
    return Path(xml_file_name).with_suffix(".json").as_posix()


def create_s3_client_unsigned(endpoint_url: str, bucket: str) -> Any:
    """
    Returns a validated Boto3 client for accessing a public S3 bucket
    (no access credentials required).

    Args:
        endpoint_url: The complete URL to use for the constructed S3 client.
        bucket: Name of S3 bucket that needs to be accessed.
                Bucket must be publicly accessible.

    Raises:
        CustomClickException: If the client could not be created or accessed.
    """
    try:
        client = boto3.client(
            service_name="s3",
            endpoint_url=endpoint_url,
            config=Config(
                signature_version=UNSIGNED,
                connect_timeout=5,
                read_timeout=TIMEOUT,
                retries={"max_attempts": 3},
            ),
        )

    except (BotoCoreError, NoCredentialsError, EndpointConnectionError) as e:
        raise CustomClickException(f"Failed to create S3 client: {e}")

    try:
        # Validate endpoint and access to an existing bucket
        client.head_bucket(Bucket=bucket)
    except (ClientError, EndpointConnectionError) as e:
        raise CustomClickException(
            f"S3 endpoint URL and/or bucket are invalid "
            f"or are not publicly accessible: {e}"
        )

    return client


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
            ),
        )

    except (BotoCoreError, NoCredentialsError, EndpointConnectionError) as e:
        raise CustomClickException(f"Failed to create S3 client: {e}")

    try:
        # Validate credentials, endpoint and access to an existing bucket
        client.head_bucket(Bucket=bucket)
    except (ClientError, EndpointConnectionError) as e:
        raise CustomClickException(
            f"S3 credentials, endpoint and/or bucket are "
            f"invalid (or credentials are not valid for bucket):"
            f" {e}"
        )

    return client


def s3_client_list_bucket_contents(
    client: Any, bucket: str, prefix: str, max_keys: int = 1000
) -> list[dict]:
    """
    Return list of all "Contents" objects in an S3 bucket matching the given prefix.
    Handles pagination automatically.

    Args:
      client: configured boto3 S3 client
      bucket: name of S3 bucket to list objects in
      prefix: key prefix to filter objects by
      max_keys: number of objects returned per page (default: 1000)
    """
    try:
        contents = []
        kwargs = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": max_keys}

        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))

            if not response.get("IsTruncated"):
                break

            kwargs["ContinuationToken"] = response["NextContinuationToken"]

        return contents

    except ClientError as err:
        raise CustomClickException(
            f"Failed to list objects in bucket '{bucket}' with prefix '{prefix}': {err}"
        )
    except Exception as err:
        raise CustomClickException(
            f"Unexpected error listing objects in bucket '{bucket}': {err}"
        )


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

        CustomEcho(
            f"Successfully exported to bucket '{bucket}' DataCite DOI record: {key}"
        )

    except ClientError as err:
        raise CustomClickException(f"{err_msg}boto3 ClientError: {err}")
    except Exception as err:
        raise CustomClickException(f"{err_msg}Unexpected error: {err}")


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
        CustomEcho(f"Wrote file: {posix_file_path}")

    except IOError as io_err:
        raise CustomClickException(f"IOError: {io_err}")

    except Exception as err:
        raise CustomClickException(f"Unexpected error: {err}")


# TODO possibly extract to new module
def parse_envicloud_url(url: str) -> tuple[str, str, str] | None:
    """
    Parse envicloud URL and return endpoint_url, bucket, and prefix.
    envicloud is the EnviDat cloud storage portal.

    Args:
         url: URL that leads to the data content
    """
    try:
        fragment = urlparse(url).fragment
        query = fragment.split("?", 1)[-1]
        params = parse_qs(query)

        bucket_url = unquote(params["bucket"][0])
        prefix = unquote(params["prefix"][0])

        parsed_bucket = urlparse(bucket_url)
        endpoint_url = f"{parsed_bucket.scheme}://{parsed_bucket.netloc}"
        bucket = parsed_bucket.path.strip("/")

        return endpoint_url, bucket, prefix

    except KeyError as err:
        CustomWarning(f"Could not parse envicloud URL '{url}': missing parameter {err}")
        return None

    except Exception as err:
        CustomWarning(f"Unexpected error parsing envicloud URL '{url}': {err}")
        return None


# TODO possibly extract to new module
# TODO review S3 and local nesting/prefix structure
def get_envicloud_objects(url: str) -> list[tuple[str, str]] | None:
    """
    Return a list of envicloud object tuples: (object_key, object_url)
    Links must have a suffix extension to be added to the list, for example '.csv'.

    Args:
        url: URL that leads to the envicloud data content
    """
    object_links = []

    parsed_url = parse_envicloud_url(url)
    if not parsed_url:
        return None

    endpoint_url, bucket, prefix = parsed_url
    client = create_s3_client_unsigned(endpoint_url, bucket)

    bucket_contents = s3_client_list_bucket_contents(client, bucket, prefix)

    for obj in bucket_contents:
        object_key = obj["Key"]
        object_url = f"{endpoint_url}/{bucket}/{object_key}"
        if Path(object_key).suffix:
            object_links.append((object_key, object_url))

    return object_links


# TODO finish WIP
# TODO handle EnviDat prefix cloud storage
def write_local_file_data_links(url: str, doi_directory: str, doi_prefix: str) -> None:
    """
    Write a bytes object to a local file.
    The content in the local file corresponds a data file resource
    passed as a URL in the DOI metadata.

    Args:
        url: URL that leads to the data content
        doi_directory: local path to directory to write the file in
        doi_prefix: prefix of the DOI
    """
    match doi_prefix:
        case "10.16904":  # EnviDat DOI prefix
            if url.startswith("https://envicloud.wsl.ch/#/?bucket="):
                pprint(get_envicloud_objects(url))

            elif (content := get_url_content(url)) and (
                file_name := Path(urlparse(url).path).name
            ):
                write_local_file(
                    content_bytes=content,
                    filename=file_name,
                    directory_path=doi_directory,
                )

        case _:
            CustomWarning(
                f"CLI does not support writing local data files for DOI "
                f"prefix: {doi_prefix}. Failed to write file '{url}' locally."
            )


class _UploadProgress:
    def __init__(self, total_bytes: int = 0) -> None:
        self._transferred = 0
        self._total_bytes = total_bytes

    def __call__(self, bytes_transferred: int) -> None:
        self._transferred += bytes_transferred
        transferred_mb = self._transferred / 1024 / 1024
        if self._total_bytes:
            total_mb = self._total_bytes / 1024 / 1024
            click.echo(
                f"\r  Progress: {transferred_mb:.1f} / {total_mb:.1f} MB", nl=False
            )
        else:
            click.echo(f"\r  Progress: {transferred_mb:.1f} MB", nl=False)


def stream_url_to_s3(
    url: str,
    bucket: str,
    key: str,
    s3_client: Any,
) -> None:
    """
    Streams content from a URL directly to an S3 bucket without loading into memory.

    Args:
        url: URL of the resource to stream.
        bucket: S3 bucket name.
        key: S3 object key.
        s3_client: configured Boto3 S3 client.
    """
    try:
        response = requests.get(url, stream=True, timeout=(10, 60))
        response.raise_for_status()
        response.raw.decode_content = True

        total_bytes = int(response.headers.get("Content-Length", 0))
        s3_client.upload_fileobj(
            Fileobj=response.raw,
            Bucket=bucket,
            Key=key,
            Callback=_UploadProgress(total_bytes),
        )
        click.echo()  # terminate progress line

        CustomEcho(f"Successfully exported to bucket '{bucket}' data file: {key}")

    except requests.exceptions.Timeout:
        CustomWarning(f"Request timed out fetching URL: '{url}'")
    except requests.exceptions.HTTPError as err:
        CustomWarning(f"HTTP error fetching URL '{url}': {err}")
    except requests.exceptions.RequestException as err:
        CustomWarning(f"Error fetching URL '{url}': {err}")
    except Exception as err:
        CustomWarning(f"Unexpected error streaming '{url}' to S3: {err}")


# TODO finish WIP
# TODO test
def s3_export_data_links(
    doi_prefix: str, url: str, s3_client: Any, bucket: str, doi_s3_dir: str
) -> None:
    """
    Export a bytes object to an object in a S3 bucket.
    The content in the S3 object corresponds a data file resource
    passed as a URL in the DOI metadata.

    Args:
        doi_prefix: prefix of the DOI
        url: URL that leads to the data content
        s3_client: configured Boto3 S3 client
        bucket: S3 bucket name
        doi_s3_dir: string with a formatted DOI (can be prepended by a key_prefix)
    """
    match doi_prefix:
        case "10.16904":  # EnviDat DOI prefix
            if url.startswith("https://envicloud.wsl.ch/#/?bucket="):
                envicloud_objects = get_envicloud_objects(url)

                if envicloud_objects:
                    for obj in envicloud_objects:
                        obj_key, obj_url = obj
                        full_key = f"{doi_s3_dir}/{obj_key}"

                        click.echo(f"Uploading to bucket '{bucket}': {obj_url}...")

                        stream_url_to_s3(
                            url=obj_url,
                            bucket=bucket,
                            key=full_key,
                            s3_client=s3_client,
                        )

                        break

            elif (content := get_url_content(url)) and (
                file_name := Path(urlparse(url).path).name
            ):
                s3_client_put_object(
                    client=s3_client,
                    body=content,
                    bucket=bucket,
                    key=f"{doi_s3_dir}/{file_name}",
                )

        case _:
            CustomWarning(
                f"CLI does not support exporting S3 objects for "
                f"DOI prefix: {doi_prefix}. Failed to write file '{url}' locally."
            )
