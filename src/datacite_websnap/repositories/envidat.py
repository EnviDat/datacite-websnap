"""
EnviDat repository module for fetching and processing data from the EnviDat portal.
"""

from pathlib import Path
from typing import Any
from urllib.parse import urlparse, unquote, parse_qs

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    BotoCoreError,
    NoCredentialsError,
    EndpointConnectionError,
)

from ..logger import CustomClickException, CustomWarning
from ..config import TIMEOUT


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


def get_envicloud_objects(url: str) -> list[tuple[str, str, int]] | None:
    """
    Return a list of envicloud object tuples: (object_key, object_url, size_bytes)
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
            object_links.append((object_key, object_url, obj.get("Size", 0)))

    return object_links
