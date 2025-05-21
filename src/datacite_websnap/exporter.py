"""
Process and export DataCite XML metadata records.
"""

import base64
from pathlib import Path
import binascii

from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    BotoCoreError,
    NoCredentialsError,
    EndpointConnectionError,
)
import boto3

from .logger import CustomClickException, CustomEcho
from .validators import S3ConfigModel
from .config import TIMEOUT


def decode_base64_xml(encoded_xml: str, file_logs: bool = False) -> bytes:
    """
    Decodes a Base64-encoded XML string and returns it as a bytes object.

    Args:
        encoded_xml: Base64-encoded XML string.
        file_logs: If True enables logging info messages and errors to a file log.
    """
    try:
        return base64.b64decode(encoded_xml)
    except binascii.Error:
        raise CustomClickException("binascii Error: Unable to decode XML", file_logs)
    except Exception as err:
        raise CustomClickException(f"Unexpected error: {err}", file_logs)


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
    doi_format = doi.replace("/", "_")

    if not key_prefix:
        return f"{doi_format}.xml"

    if key_prefix.endswith("/"):
        return f"{key_prefix}{doi_format}.xml"
    else:
        return f"{key_prefix}/{doi_format}.xml"


def create_s3_client(
    conf_s3: S3ConfigModel, file_logs: bool = False
) -> boto3.Session.client:
    """
    Return a Boto3 S3 client.

    Args:
        conf_s3: S3ConfigModel
        file_logs: If True enables logging info messages and errors to a file log.

    Raises:
        CustomClickException: If the client could not be created.

    Returns:
        boto3.client: Configured S3 client
    """
    try:
        session = boto3.Session(
            aws_access_key_id=conf_s3.aws_access_key_id,
            aws_secret_access_key=conf_s3.aws_secret_access_key,
        )
        return session.client(
            service_name="s3",
            endpoint_url=str(conf_s3.endpoint_url),
            config=Config(
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                connect_timeout=5,
                read_timeout=TIMEOUT,
                retries={"max_attempts": 3},
            ),
        )

    except (BotoCoreError, NoCredentialsError, EndpointConnectionError) as e:
        raise CustomClickException(f"Failed to create S3 client: {e}", file_logs)


def s3_client_put_object(
    client: boto3.Session.client,
    body: bytes,
    bucket: str,
    key: str,
    file_logs: bool = False,
) -> None:
    """
    Copy string as an S3 object to a S3 bucket.

    NOTE: This function will overwrite objects with the same key names!

    Args:
        client: boto3.Session.client
        body: bytes object that will be written as an S3 object's data
        bucket: name of bucket that object should be written in
        key: name (or path) of the object in the S3 bucket
        file_logs: If True enables logging info messages and errors to a file log.
    """
    err_msg = f"Failed to export key {key}: "
    try:
        response_s3 = client.put_object(Body=body, Bucket=bucket, Key=key)
    except ClientError as err:
        raise CustomClickException(f"{err_msg}boto3 ClientError: {err}", file_logs)
    except Exception as err:
        raise CustomClickException(f"{err_msg}Unexpected error: {err}", file_logs)

    if (
        status_code := response_s3.get("ResponseMetadata", {}).get("HTTPStatusCode")
    ) == 200:
        CustomEcho(
            f"Successfully exported to bucket '{bucket}' DataCite DOI record: {key}",
            file_logs,
        )
    else:
        raise CustomClickException(
            f"{err_msg}S3 client returned unexpected HTTP response "
            f"status code {status_code} for key '{key}'",
            file_logs,
        )

    return


def write_local_file(
    content_bytes: bytes,
    filename: str,
    directory_path: str | None = None,
    file_logs: bool = False,
) -> None:
    """
    Write a bytes object to a local file.

    Args:
        content_bytes: bytes object that will be written to a local file
        filename: name of file to write, be sure to include desired extension
        directory_path: path to directory to write the file in
        file_logs: If True enables logging info messages and errors to a file log.
    """
    try:
        if directory_path:
            file_path = Path(directory_path) / filename
        else:
            file_path = Path(filename)

        with open(file_path, "wb") as f:
            f.write(content_bytes)

        posix_file_path = file_path.as_posix()
        CustomEcho(f"Wrote file: {posix_file_path}", file_logs)

    except IOError as io_err:
        raise CustomClickException(f"IOError: {io_err}", file_logs)

    except Exception as err:
        raise CustomClickException(f"Unexpected error: {err}", file_logs)
