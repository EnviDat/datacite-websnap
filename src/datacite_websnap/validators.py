"""Validators for datacite-websnap."""

from pathlib import Path
from urllib.parse import urlparse
import click
from pydantic import AnyHttpUrl, ValidationError, TypeAdapter

from .config import DATACITE_DOIS_PREFIXES
from .logger import CustomBadParameter


def validate_api_url(api_url: str) -> str:
    """
    Validate and return api_url.
    Raises BadParameter exception if url does not start with 'https://.'
    """
    if not api_url.startswith("https://"):
        raise click.BadParameter(
            f"api_url '{api_url}' is invalid because it must start with 'https://'"
        )

    return api_url


def validate_page_size(page_size: int) -> int:
    """
    Validate and return page_size.
    Raises BadParameter exception if page_size is not positive or is greater than 1000.
    """
    if page_size <= 0 or page_size > 1000:
        raise click.BadParameter(
            f"page_size {page_size} is not valid, "
            f"must be a positive integer no greater than 1000."
        )

    return page_size


def validate_doi(doi: str) -> str:
    """
    Validate and return doi (without URL base).
    Raises BadParameter exception if doi does not have a "/" or if doi prefix is not in
    supported DOI prefixes (DATACITE_DOIS_PREFIXES).

    Example input doi with URL base: ""https://www.doi.org/10.16904/envidat.504"
    Return doi after passing validation: "10.16904/envidat.504"
    """
    if "/" not in doi:
        raise click.BadParameter(
            f"'{doi}' is invalid because it does not have a '/' character."
        )

    if doi.startswith("http"):
        parsed = urlparse(doi)
        if not parsed.netloc:
            raise click.BadParameter(f"'{doi}' is not a valid URL.")
        doi_bare = parsed.path.lstrip("/")
    else:
        doi_bare = doi

    prefix = doi_bare.split("/")[0]

    if prefix not in DATACITE_DOIS_PREFIXES:
        raise click.BadParameter(
            f"'{prefix}' is not one of the supported "
            f"DOI prefixes: {DATACITE_DOIS_PREFIXES}"
        )

    return doi_bare


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
    option '--destination' is 'local', or if the path does not exist.
    """
    if destination == "local" and not directory_path:
        raise CustomBadParameter(
            "'--directory-path' option must be provided when the "
            "'--destination' option is set to 'local'"
        )

    if directory_path and not Path(directory_path).is_dir():
        raise CustomBadParameter(
            f"'--directory-path' value '{directory_path}' does not exist or is not a directory."
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
