"""
CLI tool that bulk exports DataCite metadata records for a specific repository to an S3 bucket.

Also supports exporting repository records to a local machine.

*NOTE*: To use CLI in development run (installs dependencies and scripts in development mode):
    pdm install --dev

To access general CLI help in terminal execute:
    datacite-websnap --help

To access more detailed bulk-export command help in terminal execute:
    datacite-websnap bulk-export --help

Example bulk-export command:
    datacite-websnap bulk-export --client-id ethz.wsl --bucket opendata --key-prefix ethz.wsl --file-logs


# TODO add examples for doi-export
"""

import json
from pathlib import Path
from urllib.parse import urlparse

import click
from typing import Literal
import click_extra

from .logger import setup_logging, CustomEcho, CustomClickException, CustomWarning
from .config import DATACITE_API_URL, DATACITE_PAGE_SIZE
from .validators import (
    validate_at_least_one_query_param,
    validate_page_size,
    validate_bucket,
    validate_key_prefix,
    validate_directory_path,
    validate_endpoint_url,
    validate_doi,
    validate_api_url,
)
from .datacite_handler import (
    get_datacite_client,
    get_datacite_list_dois_xml,
    get_datacite_doi,
    validate_doi_eth_standard,
    get_url_content,
)
from .exporter import (
    decode_base64_xml,
    format_xml_file_name,
    write_local_file,
    create_s3_client,
    s3_client_put_object,
    format_json_file_name,
)


# TODO update docstring with doi-export command info
@click_extra.group(
    params=[],
    context_settings={
        "max_content_width": 120,
    },
)
def cli():
    """
    Tool that bulk exports DataCite metadata records from a DataCite repository as
    XML objects to an S3 bucket.

    Also supports writing DataCite metadata records as XML files to a local machine.

    To learn more about the 'bulk-export' command run:
    datacite-websnap bulk-export --help
    """
    pass


# Options used by multiple commands
def common_options(f):
    decorators = [
        click.option(
            "--destination",
            type=click.Choice(["S3", "local"]),
            default="S3",
            help="Choose where to export the DataCite XML records: "
            "'S3' (default) for an S3 bucket or 'local' for local file system.",
        ),
        click.option(
            "--profile-name",
            help="Name of a profile to use for S3 shared credentials file. "
            "If omitted then the default profile is used.",
        ),
        click.option(
            "--endpoint-url", help="Complete URL to use for the constructed S3 client."
        ),
        click.option(
            "--bucket",
            help="Name of S3 bucket that DataCite records (as S3 objects) "
            "will be written in. Must have access to bucket with configured S3 credentials.",
        ),
        click.option(
            "--key-prefix",
            help="Name of a key prefix for objects in S3 bucket. If omitted then objects are "
            "written in S3 bucket without a prefix.",
        ),
        click.option(
            "--directory-path",
            type=click.Path(exists=True, file_okay=False, dir_okay=True),
            help="Only used if exporting to local destination. Path of the local directory "
            "that DataCite records will be written in",
        ),
        click.option(
            "--file-logs",
            is_flag=True,
            default=False,
            help="Flag that enables logging info messages and errors to a file log.",
        ),
        click.option(
            "--log-level",
            default="INFO",
            type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
            help="Set the logging level.",
        ),
        click.option(
            "--api-url",
            default=DATACITE_API_URL,
            help=f"DataCite API base URL used for queries (default: {DATACITE_API_URL})",
        ),
    ]
    for decorator in decorators:
        f = decorator(f)
    return f


@cli.command(name="bulk-export")
@common_options
@click.option(
    "--doi-prefix",
    multiple=True,
    help="DataCite DOI prefix used to filter results. "
    "Accepts single or multiple prefix arguments.",
)
@click.option(
    "--client-id",
    help="DataCite repository account id used to filter results, "
    "referred to as the 'client-id' in the DataCite documentation.",
)
@click.option(
    "--early-exit",
    is_flag=True,
    default=False,
    help="If flag enabled then terminates program immediately after "
    "export error occurs. "
    "Default value is False (not enabled). "
    "If False then only logs export error and continues to try to export other "
    "DataCite XML records returned by search query "
    "to an S3 bucket or local destination.",
)
@click.option(
    "--page-size",
    type=int,
    default=DATACITE_PAGE_SIZE,
    help=f"Number of records returned per page of DataCite API response using "
    f"pagination (default: {DATACITE_PAGE_SIZE})",
)
def datacite_bulk_export(
    destination: Literal["S3", "local"] = "S3",
    profile_name: str | None = None,
    endpoint_url: str | None = None,
    bucket: str | None = None,
    key_prefix: str | None = None,
    directory_path: str | None = None,
    file_logs: bool = False,
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
    api_url: str = DATACITE_API_URL,
    doi_prefix: tuple[str, ...] = (),
    client_id: str | None = None,
    early_exit: bool = False,
    page_size: int = DATACITE_PAGE_SIZE,
) -> None:
    """
    Bulk export DataCite XML metadata records that correspond to the records for a
    particular DataCite repository or DOI prefix.

    The default behavior is to export DataCite XML records to an S3 bucket but
    command also supports downloading the records to a local machine.
    """
    # Set up logging
    setup_logging(log_level, file_logs)

    # Validate arguments
    validate_at_least_one_query_param(doi_prefix, client_id)
    validate_key_prefix(key_prefix, destination)
    validate_bucket(bucket, destination)
    validate_endpoint_url(endpoint_url, destination)
    validate_directory_path(directory_path, destination)
    validate_api_url(api_url)
    validate_page_size(page_size)

    # Validate S3 credentials and return S3 client
    s3_client = None
    if destination == "S3":
        s3_client = create_s3_client(endpoint_url, bucket, profile_name)

    # Log export information
    CustomEcho("**** Starting DataCite bulk export... ****")
    CustomEcho(f"Export destination: {destination}")
    CustomEcho(
        f"Querying DataCite API for DOIs with repository account ID: "
        f"'{client_id}' and/or prefix(es): {doi_prefix}"
    )

    # Validate client_id argument, raise error if client_id does not return successful
    # response when used to return a client from the DataCite API
    if client_id:
        get_datacite_client(api_url, client_id)

    # Create a list of dictionaries with DOIs and Base64 encoded XML strings that
    # correspond to the record results for the queried DataCite repository or DOI prefix
    xml_list = get_datacite_list_dois_xml(api_url, client_id, doi_prefix, page_size)

    # Export XML files for each record
    for doi_xml_dict in xml_list:
        try:
            doi, xml_str = next(iter(doi_xml_dict.items()))
            xml_filename = format_xml_file_name(doi, key_prefix)
            xml_decoded = decode_base64_xml(xml_str)

            match destination:
                case "S3":
                    s3_client_put_object(
                        client=s3_client,
                        body=xml_decoded,
                        bucket=bucket,
                        key=xml_filename,
                    )
                case "local":
                    write_local_file(
                        content_bytes=xml_decoded,
                        filename=xml_filename,
                        directory_path=directory_path,
                    )
                case _:
                    raise CustomClickException(
                        f"Unsupported destination: {destination}"
                    )

        except CustomClickException as err:
            if early_exit:
                raise CustomClickException(err.message)
            else:
                CustomWarning(err.message)
                continue

    CustomEcho("**** Finished DataCite bulk export ****")


# TODO implement verification function from library eth-datacite-validator
# TODO possibly wrap in try except, review error handling for helpers
@cli.command("doi-export")
@common_options
@click.option(
    "--doi",
    required=True,
    help="DataCite DOI XML record, JSON record, and associated resource data files "
    "that will be exported. Only exports DataCite DOis that pass ETH Zurich "
    "metadata standards.",
)
def datacite_single_doi_export(
    doi: str,
    destination: Literal["S3", "local"] = "S3",
    profile_name: str | None = None,
    endpoint_url: str | None = None,
    bucket: str | None = None,
    key_prefix: str | None = None,
    directory_path: str | None = None,
    file_logs: bool = False,
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
    api_url: str = DATACITE_API_URL,
) -> None:
    """
    Export a single DataCite DOI XML record, JSON record, and associated resource data
    files.

    Only exports DataCite DOIs that pass ETH Zurich metadata standards.

    The default behavior is to export DataCite records to an S3 bucket but
    command also supports downloading the records to a local machine.
    """
    # Set up logging
    setup_logging(log_level, file_logs)

    # Validate arguments
    doi_bare = validate_doi(doi)
    validate_key_prefix(key_prefix, destination)
    validate_bucket(bucket, destination)
    validate_endpoint_url(endpoint_url, destination)
    validate_directory_path(directory_path, destination)
    validate_api_url(api_url)

    # TODO implement
    # Validate S3 credentials and return S3 client
    # s3_client = None
    # if destination == "S3":
    #     s3_client = create_s3_client(endpoint_url, bucket, profile_name)

    # Log export information
    CustomEcho("**** Starting DataCite single DOI export... ****")
    CustomEcho(f"Export destination: {destination}")
    CustomEcho(f"Querying DataCite API for DOI: {doi_bare}")

    # Retrieve a DataCite DOI record
    json_resp, xml_encoded, data_links = get_datacite_doi(api_url, doi_bare)

    # Check if DataCite DOI metadata record passes validation
    xml_decoded = decode_base64_xml(xml_encoded)
    validate_doi_eth_standard(xml_decoded)

    # Format filenames
    xml_filename = format_xml_file_name(doi_bare, key_prefix)
    json_filename = format_json_file_name(xml_filename)

    # Retrieve data filenames and content
    data_files: list[tuple[str, bytes]] = [
        (Path(urlparse(url).path).name, get_url_content(url)) for url in data_links
    ]

    # TODO export DataCite API XML record, JSON record and associated resource data
    #  files to S3
    # Export record and data files
    match destination:
        case "S3":
            pass

        case "local":
            write_local_file(
                content_bytes=xml_decoded,
                filename=xml_filename,
                directory_path=directory_path,
            )
            write_local_file(
                content_bytes=json.dumps(
                    json_resp, indent=2, ensure_ascii=False
                ).encode("utf-8"),
                filename=json_filename,
                directory_path=directory_path,
            )
            for filename, content in data_files:
                write_local_file(
                    content_bytes=content,
                    filename=filename,
                    directory_path=directory_path,
                )
        case _:
            raise CustomClickException(f"Unsupported destination: {destination}")

    return
