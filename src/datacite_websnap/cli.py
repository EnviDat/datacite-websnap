"""
# TODO review description
# TODO check for all TODOs in project

CLI tool that bulk exports DataCite metadata records from a repository to an S3 bucket.

Can also be used to export repository records to a local machine.

Tool uses the PyPI package websnap, see https://pypi.org/project/websnap

*NOTE*: To use CLI in development run (installs dependencies and scripts in development mode):
    pdm install -d

# TODO add example commands
"""

import click
from typing import Literal

from .logger import setup_logging, CustomEcho, CustomClickException, CustomWarning
from .config import DATACITE_API_URL, DATACITE_PAGE_SIZE
from .validators import (
    validate_url,
    validate_at_least_one_query_param,
    validate_positive_int,
    validate_single_string_key_value,
    validate_s3_config,
    validate_bucket,
    validate_key_prefix,
)
from .datacite_handler import get_datacite_client, get_datacite_list_dois_xml
from .exporter import (
    decode_base64_xml,
    format_xml_file_name,
    write_local_file,
    create_s3_client,
    s3_client_put_object,
)


@click.group()
def cli():
    """
    Tool that bulk exports DataCite metadata records from a repository as XML objects
    to an S3 bucket.

    Also supports writing DataCite metadata records as XML files to a local machine.

    To learn more about the 'export' command run:

    datacite-websnap export --help
    """
    pass


# TODO write tests
# TODO write README
# TODO possibly add return (default None) and return types to functions in all modules
# TODO review --key-prefix option, possibly default to the prefix of the DOI
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
    "--destination",
    type=click.Choice(["S3", "local"]),
    default="S3",
    help="Choose where to export the DataCite XML records: "
    "'S3' (default) for an S3 bucket or 'local' for local file system. ",
)
@click.option(
    "--bucket",
    help="S3 bucket that DataCite XML records (as S3 objects) will be written in.",
)
@click.option(
    "--key-prefix",
    help="Optional key prefix for objects in S3 bucket. If omitted then objects are "
    "written in S3 bucket without a prefix.",
)
@click.option(
    "--directory-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path of the local directory that DataCite XML metadata records will "
    "be written in",
)
@click.option(
    "--file-logs",
    is_flag=True,
    default=False,
    help="Enables logging info messages and errors to a file log.",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Set the logging level.",
)
@click.option(
    "--early-exit",
    is_flag=True,
    default=False,
    help="If true then terminates program immediately after export error occurs. "
    "Default value is False. "
    "If False then only logs export error and continues to try to export other "
    "DataCite XML records returned by search query "
    "to an S3 bucket or local destination.",
)
def datacite_bulk_export(
    doi_prefix: tuple[str, ...] = (),
    client_id: str | None = None,
    api_url: str = DATACITE_API_URL,
    page_size: int = DATACITE_PAGE_SIZE,
    destination: Literal["S3", "local"] = "S3",
    bucket: str | None = None,
    key_prefix: str | None = None,
    directory_path: str | None = None,
    file_logs: bool = False,
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
    early_exit: bool = False,
) -> None:
    """
    Bulk export DataCite XML metadata records that correspond to the DOIs for a
    particular DataCite repository or DOI prefix.

    The default behavior is to export DataCite XML records to an S3 bucket but
    command also supports downloading the records to a local machine.
    """
    # Set up logging
    if file_logs:
        setup_logging(log_level)

    CustomEcho("**** Starting DataCite bulk export... ****", file_logs)

    # Validate arguments
    validate_at_least_one_query_param(doi_prefix, client_id, file_logs)
    validate_key_prefix(key_prefix, destination, file_logs)
    validate_bucket(bucket, destination, file_logs)
    CustomEcho(f"Export destination: {destination}", file_logs)
    CustomEcho(
        f"Querying DataCite API for DOIs with repository account ID: '{client_id}' "
        f"and/or prefix(es): {doi_prefix}",
        file_logs,
    )

    # Validate and create S3 config
    s3_client = None
    if destination == "S3":
        conf_s3 = validate_s3_config(file_logs)
        s3_client = create_s3_client(conf_s3, file_logs)

    # Validate client_id argument, raise error if client_id does not return successful
    # response when used to return a client from the DataCite API
    if client_id:
        get_datacite_client(api_url, client_id, file_logs)

    # Create a list of dictionaries with DOIs and Base64 encoded XML strings that
    # correspond to the record results for the queried DataCite repository or DOI prefix
    xml_list = get_datacite_list_dois_xml(
        api_url, client_id, doi_prefix, page_size, file_logs
    )
    doi = None

    # Export XML files for each record
    for doi_xml_dict in xml_list:
        try:
            validate_single_string_key_value(doi_xml_dict, file_logs)
            doi, xml_str = next(iter(doi_xml_dict.items()))
            xml_filename = format_xml_file_name(doi, key_prefix)
            xml_decoded = decode_base64_xml(xml_str, file_logs)

            match destination:
                case "S3":
                    s3_client_put_object(
                        client=s3_client,
                        body=xml_decoded,
                        bucket=bucket,
                        key=xml_filename,
                        file_logs=file_logs,
                    )
                case "local":
                    write_local_file(
                        content_bytes=xml_decoded,
                        filename=xml_filename,
                        directory_path=directory_path,
                        file_logs=file_logs,
                    )

        except CustomClickException as err:
            if early_exit:
                raise CustomClickException(err.message, file_logs)
            else:
                CustomWarning(err.message, file_logs)
                continue

    CustomEcho("**** Finished DataCite bulk export ****", file_logs)

    return
