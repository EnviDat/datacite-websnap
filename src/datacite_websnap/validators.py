"""Validators for datacite-websnap."""

import os
import click
from pydantic import BaseModel, AnyHttpUrl, ValidationError

from .logger import CustomBadParameter, CustomClickException


def validate_url(ctx, param, url) -> str:
    """
    Validate and return url.
    Raises BadParameter exception if url does not start with 'https://.
    """
    if not url.startswith("https://"):
        raise click.BadParameter(
            f"'{url}' is invalid because it must start with 'https://'"
        )

    return url


def validate_positive_int(ctx, param, value) -> int:
    """
    Validate and return integer.
    Raises BadParameter exception if value is not positive.
    """
    if value < 0:
        raise click.BadParameter(f"{value} must be positive integer")

    return value


def validate_at_least_one_query_param(
    doi_prefix: tuple[str, ...] | None, client_id: str | None, file_logs: bool = False
) -> None:
    """
    Validate that there is at least one query param value that is truthy.
    Raises BadParameter exception if neither "doi_prefix" "client_id"
    (truthy) arguments are provided.
    """
    if not doi_prefix and not client_id:
        raise CustomBadParameter(
            "You must provide at least one of the following options: "
            "'--doi-prefix' or '--client-id'",
            file_logs,
        )

    return


def validate_bucket(bucket, destination, file_logs: bool = False) -> str | None:
    """
    Validate and return bucket.
    Raises BadParameter exception if bucket is not truthy when
    option '--destination' is 'S3'.
    """
    if destination == "S3" and not bucket:
        raise CustomBadParameter(
            "'--bucket' option must be provided when the "
            "'--destination' option is set to 'S3'",
            file_logs,
        )

    return bucket


def validate_directory_path(
    directory_path, destination, file_logs: bool = False
) -> str | None:
    """
    Validate and return directory_path.
    Raises BadParameter exception if directory_path is not truthy when
    option '--destination' is 'local'.
    """
    if destination == "local" and not directory_path:
        raise CustomBadParameter(
            "'--directory-path' option must be provided when the "
            "'--destination' option is set to 'local'",
            file_logs,
        )

    return directory_path


def validate_key_prefix(key_prefix, destination, file_logs: bool = False) -> str:
    """
    Validate and return key_prefix.
    Raises BadParameter exception it key_prefix is truthy when option '--destination'
    is 'local'.
    """
    if destination == "local" and key_prefix:
        raise CustomBadParameter(
            "'--key_prefix' cannot be used when the"
            " '--destination' option is set to 'local'",
            file_logs,
        )

    return key_prefix


def validate_single_string_key_value(d: dict, file_logs: bool = False) -> None:
    """
    Validate that dictionary has exactly one key-value pair and both are strings.
    Raises ClickException if validation fails.
    """
    if len(d) == 1:
        key, value = list(d.items())[0]
        if not isinstance(key, str) or not isinstance(value, str):
            raise CustomClickException(
                f"Both key and value must be strings in dictionary: {d}", file_logs
            )
    else:
        raise CustomClickException(
            f"Dictionary must have only 1 key-value pair, currently has {len(d)} pairs",
            file_logs,
        )

    return


class S3ConfigModel(BaseModel):
    """
    Class with required S3 config values and their types.
    """

    endpoint_url: AnyHttpUrl
    aws_access_key_id: str
    aws_secret_access_key: str


def validate_s3_config(file_logs: bool = False) -> S3ConfigModel:
    """
    Return S3ConfigModel object after validating required environment variables.
    """
    try:
        s3_conf = {
            "endpoint_url": os.getenv("ENDPOINT_URL"),
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        }
        return S3ConfigModel(**s3_conf)
    except ValidationError as e:
        raise CustomClickException(
            f"Failed to validate S3 config environment variables, error(s): {e}",
            file_logs,
        )
    except Exception as e:
        raise CustomClickException(f"Unexpected error: {e}", file_logs)
