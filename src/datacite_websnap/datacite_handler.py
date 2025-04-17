"""
Handles interactions with DataCite API.
"""

import click
import requests

from .config import (
    DATACITE_API_CLIENTS_ENDPOINT,
    TIMEOUT,
    DATACITE_API_DOIS_ENDPOINT,
    DATACITE_PAGE_SIZE,
)


def get_url_json(url: str, params: dict | None = None, timeout: int = TIMEOUT):
    """
    Return the JSON encoded part of a response if it exists as a Python object.
    Only supports GET requests.

    Args:
        url: The URL to call return the JSON response from.
        params: An optional dictionary of query parameters to send to the URL.
        timeout: Timeout of request in seconds.
    """
    try:
        response = requests.get(url, timeout=timeout, params=params or {})
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        raise click.ClickException(f"HTTP error: {http_err}")

    except requests.exceptions.ConnectionError:
        raise click.ClickException("Network error: Unable to connect to the API.")

    except requests.exceptions.Timeout:
        raise click.ClickException(
            f"Request timeout: The API did not respond within the timeout of "
            f"{timeout} seconds."
        )

    except requests.exceptions.RequestException as req_err:
        raise click.ClickException(f"API request failed: {req_err}")

    except Exception as err:
        raise click.ClickException(f"Unexpected error: {err}")


def get_datacite_client(api_url: str, client_id: str):
    """
    Return client response from DataCite API.
    Raises error if client id does not return a successful response from the
    DataCite API.

    For DataCite API documentation used in this call see
    https://support.datacite.org/reference/get_clients-id

    Args:
        api_url: The DataCite base URL to call the API with.
        client_id: The DataCite API client id that will be used to query DataCite DOIs.
    """
    return get_url_json(f"{api_url}{DATACITE_API_CLIENTS_ENDPOINT}/{client_id}")


def extract_doi_xml(datacite_response: dict) -> list[dict]:
    """
    Returns a list of dictionaries with DOIs and extracted XML strings from a
    DataCite API data response object.

    The format of the dictionary is the values for the response keys:
      {"doi": "xml"}
      "doi" is the DataCite DOI "doi" value, for example "10.16904/envidat.27"
      "xml" is the DataCite DOI as a Base64 encoded XML string

    For more information about the expected DataCite data response object see
    DataCite API documentation: https://support.datacite.org/reference/get_dois

    Args:
        datacite_response: DataCite API data response object.
    """
    data = datacite_response.get("data", [])
    doi_xml = []

    for obj in data:
        if (xml := obj.get("attributes", {}).get("xml")) and (
            doi := obj.get("attributes", {}).get("doi")
        ):
            doi_xml.append({doi: xml})

    return doi_xml


def get_datacite_list_dois_xml(
    api_url: str,
    client_id: str | None = None,
    doi_prefix: tuple[str, ...] = (),
    page_size: int = DATACITE_PAGE_SIZE,
) -> list[dict]:
    """
    Return a list of dictionaries in the following format:
    {"doi": "xml"}
      "doi" is the DataCite DOI "doi" value, for example "10.16904/envidat.27"
      "xml" is the DataCite DOI as a Base64 encoded XML string

    The returned values correspond to the records for
    a particular DataCite repository or DOI prefix.

    Raises error if an unsuccessful response from DataCite API is returned
     or validation fails.

    For DataCite API documentation used in this call see
    https://support.datacite.org/reference/get_dois
    https://support.datacite.org/docs/pagination#method-2-cursor

    Supports the following search query params from DataCite: "prefix", "client-id"

    Args:
        api_url: The DataCite base URL to call the API with.
        client_id: The DataCite API client id used to query DataCite DOIs.
        doi_prefix: The DOI prefixes used to query DataCite DOIs.
        page_size: DataCite page size is the number of records
                   returned per page using pagination
    """
    url = f"{api_url}{DATACITE_API_DOIS_ENDPOINT}"
    params = {}

    # Query search params
    if doi_prefix:
        params["prefix"] = ",".join(doi_prefix)
    if client_id:
        params["client-id"] = client_id

    # Set param detail to "true" so that XML strings are included in response
    params["detail"] = "true"

    # Params needed for cursor-based pagination
    params["page[cursor]"] = 1
    params["page[size"] = page_size

    # Get response for first page
    resp_obj = get_url_json(url, params=params, timeout=TIMEOUT)

    # Echo total number of returned DOIs and DOIs per page
    total_records = resp_obj.get("meta", {}).get("total")
    click.echo(
        f"Total number of DataCite DOIs returned for search query: {total_records}"
    )
    click.echo(f"Number of DOIs per page: {page_size}")

    # Echo page being currently processed
    pages = 1
    total_pages = resp_obj.get("meta", {}).get("totalPages")
    click.echo(f"Currently processing page {pages}/{total_pages}...")

    # Extract DOIs and XML strings for first page
    xml_lst = []
    if resp_xml_lst := extract_doi_xml(resp_obj):
        xml_lst.extend(resp_xml_lst)

    # Extract DOIs and XML strings for subsequent pages
    while True:
        if pages < total_pages:
            click.echo(f"Currently processing page {pages + 1}/{total_pages}...")

        # Get next link using cursor-based pagination
        next_link = resp_obj.get("links", {}).get("next")
        if not next_link:
            break

        resp_obj = get_url_json(next_link, params={"detail": "true"}, timeout=TIMEOUT)
        if resp_xml_lst := extract_doi_xml(resp_obj):
            xml_lst.extend(resp_xml_lst)

        pages += 1

    # Validate processed output matches number of records and pages in
    # response "meta" object
    if total_pages != pages:
        raise click.ClickException(
            f"Pages retrieved ({pages}) does not match the total number of pages "
            f"expected in response 'meta' object: {total_pages}, for DataCite API call"
            f"see {next_link}"
        )

    xml_lst_length = len(xml_lst)
    if total_records != xml_lst_length:
        raise click.ClickException(
            f"Total number of XML records retrieved ({xml_lst_length}) does not match "
            f"the total number of records expected in 'meta' object: {total_records}, "
            f"for DataCite API call see {next_link}"
        )

    return xml_lst
