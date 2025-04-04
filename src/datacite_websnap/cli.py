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

import pprint

# TODO implement early exit option for commands (like websnap)
# TODO implement logging with custom logger (like websnap)

import click

from .constants import DATACITE_API_URL
from .validators import validate_url, validate_at_least_one_query_param, validate_bucket
from .datacite_handler import get_datacite_client


@click.group()
def cli():
    """
    Tool that bulk exports DataCite metadata records from a repository to an S3 bucket.
    """
    pass


# TODO add support for DOI prefix as well, can be more than one
# TODO possibly validate that api_url is a URL using pydantic AnyURL
# TODO implement error handling that wraps all logic
# TODO implement option for a key prefix in S3 config handling
# TODO local-config option as a flag so that by default a S3 config is written
#  instead of a config for a local machine
# TODO implement option for a directory, use directory in local-config handling
# TODO determine how XML file names should be formatted
@cli.command(name="config-writer")
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
    "--bucket",
    help="Bucket that DataCite XML files (as S3 objects) will be written in.",
)
@click.option("--key-prefix", help="Optional key prefix for objects in bucket.")
@click.option(
    "--local-config",
    is_flag=True,
    default=False,
    help="Enables writing config that supports exporting DataCite "
    "records to a local machine.",
)
@click.option(
    "--local-directory",
    help="Name of the local directory that file will be written in "
    "if '--local-config' option is enabled",
)
@click.option(
    "--api-url",
    default=DATACITE_API_URL,
    help=f"DataCite base API URL (default: {DATACITE_API_URL})",
    callback=validate_url,
)
def datacite_config_writer(
    doi_prefix: tuple[str, ...] = (),
    client_id: str | None = None,
    bucket: str | None = None,
    key_prefix: str | None = None,
    local_config: bool = False,
    local_directory: str | None = None,
    api_url: str = DATACITE_API_URL,
):
    """
    Write a JSON config used by package websnap with API URLs that correspond to the
    DOIs for a DataCite repository.

    To learn more about how DataCite assigns each repository its own client id please
    see: https://support.datacite.org/reference/get_clients-id

    To learn more about writing configuration files for the package websnap please see:
    https://github.com/EnviDat/websnap?tab=readme-ov-file#websnap
    """
    # Validate that at least one query param value is truthy
    validate_at_least_one_query_param(doi_prefix, client_id)

    # Validate that bucket argument is truthy if not using local_config option
    validate_bucket(bucket, local_config)

    # Validate client_id argument
    # Raise error if client id does not return successful response when used to
    # return a client from the DataCite API
    if client_id:
        get_datacite_client(api_url, client_id)

    # TODO remove
    test = get_datacite_client(api_url, client_id)
    # Make the world pretty and colorful
    # click.echo(pprint.pformat(test, indent=2, width=80))
    click.echo(click.style(pprint.pformat(test, indent=2, width=80), fg="blue"))

    # TODO WIP start here

    # TODO get a list of DOIs for a client using this DataCite API endpoint:
    #  https://support.datacite.org/reference/get_dois

    # TODO then write config (S3 or local machine)


# TODO write command "export" to write DataCite records to S3 bucket or local machine,
#  have options to review and pass config
# TODO have option to use --s3_uploader (consistent with websnap)
# TODO check that config is valid for action selected (S3 or local usage)
# TODO implement option for a bucket, add check that it should be mandatory
#  unless local-config used
