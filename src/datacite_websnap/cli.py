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

from .constants import DATACITE_API_URL, DATACITE_PAGE_SIZE
from .validators import (
    validate_url,
    validate_at_least_one_query_param,
    validate_positive_int,
    validate_single_string_key_value,
)
from .datacite_handler import get_datacite_client, get_datacite_list_dois_xml
from .writer import decode_base64_xml, format_xml_file_name, write_file


@click.group()
def cli():
    """
    Tool that bulk exports DataCite metadata records from a repository as XML objects
    to an S3 bucket.

    Also supports writing DataCite metadata records as XML files to a local machine.
    """
    pass


# TODO remove unneeded echo statements here and in other modules
# TODO add logic to write DataCite records to S3 bucket
# TODO add support for DOI prefix as well, can be more than one
# TODO possibly validate that api_url is a URL using pydantic AnyURL
# TODO implement error handling that wraps all logic with an
#  early exit option like websnap
# TODO determine how XML file names should be formatted
# TODO in a later version possibly zip files
# TODO revise docstring
@cli.command(name="export")
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
    "--page-size",
    type=int,
    default=DATACITE_PAGE_SIZE,
    help=f"DataCite page size is the number of records returned per page using "
    f"pagination (default: {DATACITE_PAGE_SIZE})",
    callback=validate_positive_int,
)
@click.option(
    "--directory-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path of the local directory that DataCite XML metadata records will "
    "be written in",
)
def datacite_bulk_export(
    doi_prefix: tuple[str, ...] = (),
    client_id: str | None = None,
    api_url: str = DATACITE_API_URL,
    page_size: int = DATACITE_PAGE_SIZE,
    directory_path: str | None = None,
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

    # Create a list of dictionaries with DOIs and XML strings that correspond to
    # the record results for the queried DataCite repository or DOI prefix
    xml_list = get_datacite_list_dois_xml(api_url, client_id, doi_prefix, page_size)

    # TODO start dev here
    # TODO FIRST TASK: ****test local output in DataCite Fabrica test!!!!***
    # Write XML files for each record

    # TODO implement and test for all records
    # for doi_xml_dict in xml_list:

    xml_test_list = xml_list[:5]
    for doi_xml_dict in xml_test_list:
        validate_single_string_key_value(doi_xml_dict)

        doi, xml_str = next(iter(doi_xml_dict.items()))
        xml_filename = format_xml_file_name(doi)
        xml_decoded = decode_base64_xml(xml_str)

        write_file(xml_decoded, xml_filename, directory_path)


# TODO remove command
# TODO then write config (websnap S3) in command "config-writer" with new support
#  for path configuration
# TODO write supporting functions in module "config_writer.py"
@click.command(name="config-writer")
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
