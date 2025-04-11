"""Validators for datacite-websnap."""

import os

import click
from pydantic import BaseModel, AnyHttpUrl, ValidationError
from dotenv import load_dotenv


def validate_url(ctx, param, url):
    """
    Validate and return url.
    Raises BadParameter exception if url does not start with 'https://.
    """
    if not url.startswith("https://"):
        raise click.BadParameter(
            f"'{url}' is invalid because it must start with 'https://'"
        )

    return url


def validate_positive_int(ctx, param, value):
    """
    Validate and return integer.
    Raises BadParameter exception if value is not positive.
    """
    if value < 0:
        raise click.BadParameter(f"{value} must be positive integer")

    return value


def validate_at_least_one_query_param(
    doi_prefix: tuple[str, ...] | None, client_id: str | None
):
    """
    Validate that there is at least one query param value that is truthy.
    Raises BadParameter exception if neither "doi_prefix" "client_id"
    (truthy) arguments are provided.
    """
    if not doi_prefix and not client_id:
        raise click.BadParameter(
            "You must provide at least one of the following options: "
            "'--doi-prefix' or '--client-id'"
        )


def validate_bucket(bucket, destination):
    """
    Validate and return bucket.
    Raises BadParameter exception if bucket is not truthy when
    option '--destination' is 'S3'.
    """
    if destination == "S3" and not bucket:
        raise click.BadParameter(
            "'--bucket' option must be provided when the "
            "'--destination' option is set to 'S3'"
        )

    return bucket


def validate_single_string_key_value(d: dict):
    """
    Validate that dictionary has exactly one key-value pair and both are strings.
    Raises ClickException if validation fails.

    Args:
        d: The dictionary to validate.
    """
    if len(d) == 1:
        key, value = list(d.items())[0]
        if not isinstance(key, str) or not isinstance(value, str):
            raise click.ClickException(
                f"Both key and value must be strings in dictionary: {d}"
            )
    else:
        raise click.ClickException(f"Dictionary must have only one key-value pair: {d}")


class S3ConfigModel(BaseModel):
    """
    Class with required S3 config values and their types.
    """

    endpoint_url: AnyHttpUrl
    aws_access_key_id: str
    aws_secret_access_key: str


def validate_s3_config() -> S3ConfigModel:
    """
    Return S3ConfigModel object after validating required environment variables.
    """
    try:
        load_dotenv()
        s3_conf = {
            "endpoint_url": os.getenv("ENDPOINT_URL"),
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        }
        return S3ConfigModel(**s3_conf)
    except ValidationError as e:
        raise click.ClickException(
            f"Failed to validate S3 config environment variables, error(s): {e}"
        )
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")
