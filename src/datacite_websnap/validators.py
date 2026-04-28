"""Validators for datacite-websnap."""

import click
from pydantic import AnyHttpUrl, ValidationError, TypeAdapter

from .logger import CustomBadParameter


def validate_url(ctx: click.Context, param: click.Parameter, url: str) -> str:
    """
    Validate and return url.
    Raises BadParameter exception if url does not start with 'https://.'
    """
    if not url.startswith("https://"):
        raise click.BadParameter(
            f"'{url}' is invalid because it must start with 'https://'"
        )

    return url


def validate_page_size(ctx: click.Context, param: click.Parameter, value: int) -> int:
    """
    Validate and return integer.
    Raises BadParameter exception if value is not positive or is greater than 1000.
    """
    if value <= 0 or value > 1000:
        raise click.BadParameter("Must be positive integer no greater than 1000.")

    return value


def validate_at_least_one_query_param(
    doi_prefix: tuple[str, ...] | None, client_id: str | None
) -> None:
    """
    Validate that there is at least one query param value that is truthy.
    Raises BadParameter exception if neither "doi_prefix" "client_id"
    (truthy) arguments are provided.
    """
    if not doi_prefix and not client_id:
        raise CustomBadParameter(
            "You must provide at least one of the following options: "
            "'--doi-prefix' or '--client-id'"
        )

    return


def validate_bucket(bucket, destination) -> str | None:
    """
    Validate and return bucket.
    Raises BadParameter exception if bucket is not truthy when
    option '--destination' is 'S3'.
    """
    if destination == "S3" and not bucket:
        raise CustomBadParameter(
            "'--bucket' option must be provided when the "
            "'--destination' option is set to 'S3'"
        )

    return bucket


def validate_endpoint_url(endpoint_url, destination) -> str | None:
    """
    Validate and return endpoint_url, it must be an http or https URL.
    Raises BadParameter exception if endpoint_url is not truthy when
    option '--destination' is 'S3'.
    """
    if destination == "S3" and not endpoint_url:
        raise CustomBadParameter(
            "'--endpoint-url' option must be provided when the "
            "'--destination' option is set to 'S3'"
        )

    if endpoint_url:
        try:
            ta = TypeAdapter(AnyHttpUrl)
            validated = ta.validate_python(endpoint_url)
            return str(validated)

        except ValidationError:
            raise CustomBadParameter(
                f"'--endpoint-url' value '{endpoint_url}' is not a valid HTTP/HTTPS URL"
            )

    return endpoint_url


def validate_directory_path(directory_path, destination) -> str | None:
    """
    Validate and return directory_path.
    Raises BadParameter exception if directory_path is not truthy when
    option '--destination' is 'local'.
    """
    if destination == "local" and not directory_path:
        raise CustomBadParameter(
            "'--directory-path' option must be provided when the "
            "'--destination' option is set to 'local'"
        )

    return directory_path


def validate_key_prefix(key_prefix, destination) -> str:
    """
    Validate and return key_prefix.
    Raises BadParameter exception it key_prefix is truthy when option '--destination'
    is 'local'.
    """
    if destination == "local" and key_prefix:
        raise CustomBadParameter(
            "'--key_prefix' cannot be used when the"
            " '--destination' option is set to 'local'"
        )

    return key_prefix
