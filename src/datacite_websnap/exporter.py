"""
Process and export DataCite XML metadata records.
"""

import base64
import os

import click
from lxml import etree
import boto3

from datacite_websnap.validators import S3ConfigModel


def decode_base64_xml(encoded_xml: str) -> str:
    """
    Decodes a Base64-encoded XML string and returns it as a
    pretty-print formatted XML string.

    Args:
        encoded_xml: Base64-encoded XML string.
    """
    try:
        decoded_bytes = base64.b64decode(encoded_xml)
        root = etree.fromstring(decoded_bytes)

        return etree.tostring(
            root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        ).decode("utf-8")

    except UnicodeDecodeError:
        raise click.ClickException("UnicodeDecode Error: Unable to decode XML")

    except etree.XMLSyntaxError as syntax_err:
        raise click.ClickException(
            f"XMLSyntax Error: Unable to decode XML: {syntax_err}"
        )

    except Exception as err:
        raise click.ClickException(f"Unexpected error: {err}")


def format_xml_file_name(doi: str) -> str:
    """
    Format "doi" value into an XML filename.
    "/" replaced with "_" and ".xml" appended to the filename.

    Example input: "10.16904/envidat.31"
    Example output: "10.16904_envidat.31.xml"

    Args:
        doi: "doi" string, example "10.16904/envidat.31"
    """
    doi_format = doi.replace("/", "_")
    return f"{doi_format}.xml"


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
    return session.client(service_name="s3", endpoint_url=str(conf_s3.endpoint_url))


# TODO add error handling
# TODO test
def s3_client_put_object(
    client: boto3.Session.client, body: str, bucket: str, key: str
):
    """
    Copy string as an S3 object to a S3 bucket.

    NOTE: This function will overwrite objects with the same key names!

    Args:
        client: boto3.Session.client
        body: string that will be written as an S3 object's data
        bucket: name of bucket that object should be written in
        key: name (or path) of the object in the S3 bucket
    """
    response_s3 = client.put_object(Body=body, Bucket=bucket, Key=key)

    if (
        status_code := response_s3.get("ResponseMetadata", {}).get("HTTPStatusCode")
    ) == 200:
        click.echo(f"Successfully exported DataCite DOI to bucket '{bucket}': {key}")
    else:
        click.ClickException(
            f"S3 client returned unexpected HTTP response {status_code} for key '{key}'"
        )


def write_local_file(
    content_str: str, filename: str, directory_path: str | None = None
):
    """
    Write a string to a file.
    """
    try:
        if directory_path:
            file_path = os.path.join(directory_path, filename)
        else:
            file_path = filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content_str)

        click.echo(f"Wrote file: {file_path}")

    except IOError as io_err:
        raise click.ClickException(f"IOError: {io_err}")

    except Exception as err:
        raise click.ClickException(f"Unexpected error: {err}")
