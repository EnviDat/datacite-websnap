"""Validators for datacite-websnap."""

import click


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
