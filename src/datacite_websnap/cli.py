"""
CLI tool that exports DataCite records to an S3 bucket.

Also supports exporting records to a local machine.


**** NOTE *****
To use CLI in development run (installs dependencies and scripts in development mode):
    pdm install --dev


# ---- General Commands ----
    datacite-websnap bulk-export --help
To access general CLI help in terminal execute:
    datacite-websnap --help


# ---- bulk-export command ----
To access more detailed bulk-export command help in terminal execute:
    datacite-websnap bulk-export --help

Example bulk-export command:
    datacite-websnap bulk-export --client-id ethz.wsl --bucket opendata --key-prefix wsl --file-logs


# ---- doi-export command ----
To access more detailed doi-export command help in terminal execute:
    datacite-websnap doi-export --help

Example doi-export command:
     datacite-websnap doi-export  --doi "https://www.doi.org/10.16904/envidat.692" --file-logs --bucket metadata --endpoint-url "https://examplecloud.com"  --key-prefix wsl
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal, Any
from pathlib import Path

import click
import click_extra

from .logger import setup_logging, CustomEcho, CustomClickException, CustomWarning
from .config import (
    DATACITE_API_URL,
    DATACITE_PAGE_SIZE,
    THREADING_UPLOAD_THRESHOLD,
    THREADING_UPLOAD_MAX_WORKERS,
)
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
from .datacite_api import (
    get_datacite_client,
    get_datacite_list_dois_xml,
    get_datacite_doi,
    validate_doi_eth_standard,
)
from .exporter import (
    decode_base64_xml,
    format_xml_file_name,
    write_local_file,
    create_s3_client,
    s3_client_put_object,
    s3_key_exists,
    format_json_file_name,
    write_local_file_data_links,
    resolve_data_link,
    echo_resolved_data_links,
    upload_data_link,
    format_doi_stem,
)


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

    To learn more about the 'doi-export' command run:
    datacite-websnap doi-export --help
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
                raise err
            else:
                CustomWarning(err.message)
                continue

    CustomEcho("**** Finished DataCite bulk export ****")


def _execute_uploads(
    to_upload: list[tuple[str, str, int]],
    s3_client: Any,
    bucket: str,
) -> None:
    """
    Upload data files to S3 bucket.

    Uses a pool of threads to upload data files if
    the length of to_upload exceeds THREADING_UPLOAD_THRESHOLD.

    Args:
       to_upload: List of tuples which information about
                  data files to upload (s3_key, download_url, size)
        s3_client: validated Boto3 S3 client created using a shared AWS credentials file
        bucket: name of S3 bucket that DataCite records (as S3 objects) will be written
                in, must have access to bucket with configured S3 credentials
    """
    if len(to_upload) > THREADING_UPLOAD_THRESHOLD:
        with ThreadPoolExecutor(max_workers=THREADING_UPLOAD_MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    upload_data_link, s3_key, download_url, s3_client, bucket
                ): s3_key
                for s3_key, download_url, _ in to_upload
            }
            for future in as_completed(futures):
                future.result()
    else:
        for s3_key, download_url, _ in to_upload:
            upload_data_link(
                s3_key, download_url, s3_client, bucket, show_upload_progress=True
            )
            click.echo("")


def _upload_data_links_s3(
    doi_bare: str,
    doi_prefix: str,
    data_links: list[str],
    doi_s3_dir: str,
    s3_client: Any,
    bucket: str,
) -> None:
    """
    Export DOI data files to S3 storage.
    Confirm with users if they want to overwrite existing S3 objects.

    Args:
        doi_bare: DOI (without URL base), example: "10.16904/envidat.504"
        doi_prefix: DOI prefix, example: "10.16904"
        data_links: list of links to data files for DOI from DataCite API
        doi_s3_dir: key_prefix if passed as argument prepended to formatted DOI string
        s3_client: validated Boto3 S3 client created using a shared AWS credentials file
        bucket: name of S3 bucket that DataCite records (as S3 objects) will be written
                in, must have access to bucket with configured S3 credentials
    """
    resolved = []
    for url in data_links:
        resolved.extend(resolve_data_link(doi_prefix, url, doi_s3_dir))

    if not resolved:
        return

    key_exists = {
        s3_key: s3_key_exists(s3_client, bucket, s3_key)
        for s3_key, download_url, size in resolved
    }
    existing_data = [
        (s3_key, download_url, size)
        for s3_key, download_url, size in resolved
        if key_exists[s3_key]
    ]
    new_data = [
        (s3_key, download_url, size)
        for s3_key, download_url, size in resolved
        if not key_exists[s3_key]
    ]

    to_upload = []

    if new_data:
        echo_resolved_data_links(doi_bare, new_data)
        if click.confirm(
            click.style(
                f"Proceed with uploading new data object(s) to bucket '{bucket}'?",
                fg="cyan",
                bold=True,
            )
        ):
            to_upload.extend(new_data)
        click.echo("")

    if existing_data:
        echo_resolved_data_links(doi_bare, existing_data, "yellow")
        if click.confirm(
            click.style(
                f"The {len(existing_data)} data object(s) already exist in "
                f"bucket '{bucket}'. Overwrite?",
                fg="yellow",
                bold=True,
            )
        ):
            to_upload.extend(existing_data)
        click.echo("")

    _execute_uploads(to_upload, s3_client, bucket)


def _export_doi_s3(
    doi_bare: str,
    doi_prefix: str,
    xml_decoded: bytes,
    json_resp: dict,
    data_links: list[str],
    s3_client: Any,
    bucket: str,
    key_prefix: str | None,
) -> None:
    """
    Export DOI metadata records and data files to S3 storage.

    Args:
        doi_bare: DOI (without URL base), example: "10.16904/envidat.504"
        doi_prefix: DOI prefix, example: "10.16904"
        xml_decoded: DataCite DOI "xml" value decoded and represented as a bytes object
        json_resp: JSON response for DOI from DataCite API
        data_links: list of links to data files for DOI from DataCite API
        s3_client: validated Boto3 S3 client created using a shared AWS credentials file
        bucket: name of S3 bucket that DataCite records (as S3 objects) will be written
                in, must have access to bucket with configured S3 credentials
        key_prefix: name of a key prefix for objects in S3 bucket, if omitted then
                    objects are written in S3 bucket without a prefix
    """
    doi_stem = format_doi_stem(doi_bare)
    doi_s3_dir = f"{key_prefix}/{doi_stem}" if key_prefix else doi_stem

    xml_key = f"{doi_s3_dir}/{doi_stem}.xml"
    json_key = f"{doi_s3_dir}/{doi_stem}.json"

    existing_metadata = [
        k for k in (xml_key, json_key) if s3_key_exists(s3_client, bucket, k)
    ]

    should_put_metadata = True
    if existing_metadata:
        click.echo("")
        click.echo(
            click.style(
                f"The following metadata object(s) already exist in bucket '{bucket}':",
                fg="yellow",
                bold=True,
            )
        )
        for k in existing_metadata:
            click.echo(f"  {k}")
        should_put_metadata = click.confirm(
            click.style(
                "Overwrite existing metadata object(s)?", fg="yellow", bold=True
            )
        )
        click.echo("")

    if should_put_metadata:
        s3_client_put_object(
            client=s3_client, body=xml_decoded, bucket=bucket, key=xml_key
        )
        s3_client_put_object(
            client=s3_client,
            body=json.dumps(json_resp, indent=2, ensure_ascii=False).encode("utf-8"),
            bucket=bucket,
            key=json_key,
        )

    _upload_data_links_s3(
        doi_bare, doi_prefix, data_links, doi_s3_dir, s3_client, bucket
    )


def _export_doi_local(
    doi_bare: str,
    doi_prefix: str,
    xml_decoded: bytes,
    json_resp: dict,
    data_links: list[str],
    directory_path: str,
) -> None:
    """
    Export DOI metadata records and data files to local machine.

    Args:
        doi_bare: DOI (without URL base), example: "10.16904/envidat.504"
        doi_prefix: DOI prefix, example: "10.16904"
        xml_decoded: DataCite DOI "xml" value decoded and represented as a bytes object
        json_resp: JSON response for DOI from DataCite API
        data_links: list of links to data files for DOI from DataCite API
        directory_path: path of the local directory that DataCite records will be
                        written in
    """
    xml_filename = format_xml_file_name(doi_bare)
    json_filename = format_json_file_name(xml_filename)

    doi_dir = Path(directory_path) / Path(xml_filename).stem
    doi_dir.mkdir(exist_ok=True)
    doi_directory = str(doi_dir)

    write_local_file(
        content_bytes=xml_decoded,
        filename=xml_filename,
        directory_path=doi_directory,
    )
    write_local_file(
        content_bytes=json.dumps(json_resp, indent=2, ensure_ascii=False).encode(
            "utf-8"
        ),
        filename=json_filename,
        directory_path=doi_directory,
    )
    for url in data_links:
        write_local_file_data_links(url, doi_directory, doi_prefix)


@cli.command("doi-export")
@common_options
@click.option(
    "--doi",
    required=True,
    help="DOI that corresponds to DataCite DOI XML record, JSON record, and associated "
    "resource data files that will be exported. Only exports DataCite DOIs that "
    "pass ETH Zurich metadata standards.",
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
    doi_bare, doi_prefix = validate_doi(doi)
    validate_key_prefix(key_prefix, destination)
    validate_bucket(bucket, destination)
    validate_endpoint_url(endpoint_url, destination)
    validate_directory_path(directory_path, destination)
    validate_api_url(api_url)

    # Validate S3 credentials and return S3 client
    s3_client = None
    if destination == "S3":
        s3_client = create_s3_client(endpoint_url, bucket, profile_name)

    # Log export information
    click.echo("")
    title = "Starting DataCite single DOI export..."
    click.echo(click.style("─" * len(title), fg="cyan"))
    CustomEcho(title)
    CustomEcho(f"Export destination: {destination}")
    CustomEcho(f"Querying DataCite API for DOI: {doi_bare}")

    # Retrieve a DataCite DOI record
    json_resp, xml_encoded, data_links = get_datacite_doi(api_url, doi_bare)

    # Check if DataCite DOI metadata record passes validation
    xml_decoded = decode_base64_xml(xml_encoded)
    validate_doi_eth_standard(xml_decoded, doi_bare)

    # Export record and data files
    match destination:
        case "S3":
            _export_doi_s3(
                doi_bare=doi_bare,
                doi_prefix=doi_prefix,
                xml_decoded=xml_decoded,
                json_resp=json_resp,
                data_links=data_links,
                s3_client=s3_client,
                bucket=bucket,
                key_prefix=key_prefix,
            )
        case "local":
            _export_doi_local(
                doi_bare=doi_bare,
                doi_prefix=doi_prefix,
                xml_decoded=xml_decoded,
                json_resp=json_resp,
                data_links=data_links,
                directory_path=directory_path,
            )
        case _:
            raise CustomClickException(f"Unsupported destination: {destination}")
