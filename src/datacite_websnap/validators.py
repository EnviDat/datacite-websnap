"""Validators for datacite-websnap."""

import click


def validate_url(ctx, param, url):
    """
    Validate and return url.
    Raises BadParameter exception if url does not start with 'https://."""
    if not url.startswith("https://"):
        raise click.BadParameter(
            f"'{url}' is invalid because it must start with 'https://'"
        )
    return url



