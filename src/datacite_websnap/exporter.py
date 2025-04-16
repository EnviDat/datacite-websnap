"""
Process and export DataCite XML metadata records.
"""

import base64
import os

import click
from botocore.config import Config
from botocore.exceptions import ClientError
import boto3

from datacite_websnap.validators import S3ConfigModel


def decode_base64_xml(encoded_xml: str) -> bytes:
    """
    Decodes a Base64-encoded XML string and returns it as a bytes object.

    Args:
        encoded_xml: Base64-encoded XML string.
    """
    try:
        return base64.b64decode(encoded_xml)
    except UnicodeDecodeError:
        raise click.ClickException("UnicodeDecode Error: Unable to decode XML")
    except Exception as err:
        raise click.ClickException(f"Unexpected error: {err}")


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


# TODO add error handling
def create_s3_client(conf_s3: S3ConfigModel):
    """
    Return a Boto3 S3 client.

    Args:
        conf_s3: S3ConfigModel
    """
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
        ),
    )


def s3_client_put_object(
    client: boto3.Session.client, body: bytes, bucket: str, key: str
):
    """
    Copy string as an S3 object to a S3 bucket.

    NOTE: This function will overwrite objects with the same key names!

    Args:
        client: boto3.Session.client
        body: bytes object that will be written as an S3 object's data
        bucket: name of bucket that object should be written in
        key: name (or path) of the object in the S3 bucket
    """
    try:
        response_s3 = client.put_object(Body=body, Bucket=bucket, Key=key)
    except ClientError as err:
        raise click.ClickException(f"boto3 ClientError: {err}")
    except Exception as err:
        raise click.ClickException(f"Unexpected error: {err}")

    if (
        status_code := response_s3.get("ResponseMetadata", {}).get("HTTPStatusCode")
    ) == 200:
        click.echo(
            f"Successfully exported DataCite DOI record to bucket '{bucket}': {key}"
        )
    else:
        click.ClickException(
            f"S3 client returned unexpected HTTP response {status_code} for key '{key}'"
        )


def write_local_file(
    content_bytes: bytes, filename: str, directory_path: str | None = None
):
    """
    Write a bytes object to a local file.

    Args:
        content_bytes: bytes object that will be written to a local file
        filename: name of file to write, be sure to include desired extension
        directory_path: path to directory to write the file in
    """
    try:
        if directory_path:
            file_path = os.path.join(directory_path, filename)
        else:
            file_path = filename

        with open(file_path, "wb") as f:
            f.write(content_bytes)

        click.echo(f"Wrote file: {file_path}")

    except IOError as io_err:
        raise click.ClickException(f"IOError: {io_err}")

    except Exception as err:
        raise click.ClickException(f"Unexpected error: {err}")
