"""Validators for datacite-websnap."""

import click


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


def validate_url(ctx, param, url):
    """
    Validate and return url.
    Raises BadParameter exception if url does not start with 'https://."""
    if not url.startswith("https://"):
        raise click.BadParameter(
            f"'{url}' is invalid because it must start with 'https://'"
        )
    return url
