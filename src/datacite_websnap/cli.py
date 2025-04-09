"""
# TODO review description

CLI tool that bulk exports DataCite metadata records from a repository to an S3 bucket.

Can also be used to export repository records to a local machine.

Tool uses the PyPI package websnap, see https://pypi.org/project/websnap

*NOTE*: To use CLI in development run (installs dependencies and scripts in development mode):
    pdm install -d

Example usage for command 'config-writer' that writes a websnap config file with the
URLs corresponding to DataCite metadata records:
    datacite-websnap config-writer --client-id ethz.wsl --bucket exampledata
"""
# TODO implement early exit option for commands (like websnap)
# TODO implement logging with custom logger (like websnap)

import click

from .constants import DATACITE_API_URL
from .validators import validate_url, validate_at_least_one_query_param
from .datacite_handler import get_datacite_client, get_datacite_list_dois


@click.group()
def cli():
    """
    Tool that bulk exports DataCite metadata records from a repository to an S3 bucket.
    """
    pass


# TODO add support for DOI prefix as well, can be more than one
# TODO possibly validate that api_url is a URL using pydantic AnyURL
# TODO implement error handling that wraps all logic
# TODO determine how XML file names should be formatted
# TODO in a later version possibly zip files
@cli.command(name="download")
@click.option(
    "--doi-prefix",
    multiple=True,
    help="DataCite DOI prefix. Accepts multiple prefix arguments.",
)
@click.option(
    "--client-id",
    help="DataCite repository account id, referred to as the client id in the "
    "DataCite documentation.",
)
@click.option(
    "--api-url",
    default=DATACITE_API_URL,
    help=f"DataCite base API URL (default: {DATACITE_API_URL})",
    callback=validate_url,
)
@click.option(
    "--local-directory",
    help="Path of the local directory that DataCite XML metadata records will "
    "be written in",
)
def datacite_bulk_download(
    doi_prefix: tuple[str, ...] = (),
    client_id: str | None = None,
    api_url: str = DATACITE_API_URL,
    local_directory: str | None = None,
):
    """
    Bulk download DataCite XML metadata records that correspond to the DOIs for a
    particular DataCite repository or DOI prefix.
    """
    # Validate that at least one query param value is truthy
    validate_at_least_one_query_param(doi_prefix, client_id)

    # Validate client_id argument, raise error if client_id does not return successful
    # response when used to return a client from the DataCite API
    if client_id:
        get_datacite_client(api_url, client_id)

    # Create a list of DOIs that belong to the queried DataCite repository or DOI prefix
    dois = get_datacite_list_dois(api_url, client_id, doi_prefix)

    # TODO start dev here
    # TODO check DataCite API for rate limiting
    # TODO call DataCite API for each DOI
    # TODO write XML files for each DOI


# TODO WIP finish
# TODO then write config (websnap S3) in command "config-writer" with new support
#  for path configuration
@cli.command(name="config-writer")
@click.option(
    "--bucket",
    required=True,
    help="Bucket that DataCite XML files (as S3 objects) will be written in.",
)
@click.option("--key-prefix", help="Optional key prefix for objects in bucket.")
def datacite_config_writer(bucket: str, key_prefix: str | None = None):
    """
    Write a JSON config used by package websnap with files that correspond to the
    DOIs for a DataCite repository.
    """
    click.echo(f"bucket: {bucket}")
    click.echo(f"key-prefix: {key_prefix}")


# TODO write command "export" to write DataCite records to S3 bucket
