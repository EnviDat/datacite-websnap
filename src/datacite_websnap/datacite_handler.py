"""
Handles interactions with DataCite API.
"""

import click
import requests

from .constants import (
    DATACITE_API_CLIENTS_ENDPOINT,
    TIMEOUT,
    DATACITE_API_DOIS_ENDPOINT,
)


class APIError(click.ClickException):
    """Custom Click exception for API related errors."""

    def __init__(self, message):
        super().__init__(message)


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
        raise APIError(f"HTTP error: {http_err}")

    except requests.exceptions.ConnectionError:
        raise APIError("Network error: Unable to connect to the API.")

    except requests.exceptions.Timeout:
        raise APIError(
            f"Request timeout: The API did not respond in within the timeout of "
            f"{timeout} seconds."
        )

    except requests.exceptions.RequestException as req_err:
        raise APIError(f"API request failed: {req_err}")

    except Exception as err:
        raise APIError(f"Unexpected error: {err}")


def get_datacite_client(
    api_url: str, client_id: str, endpoint: str = DATACITE_API_CLIENTS_ENDPOINT
):
    """
    Return client response from DataCite API.
    Raises error if client id does not return a successful response from the
    DataCite API.

    For DataCite API documentation used in this call see
    https://support.datacite.org/reference/get_clients-id

    Args:
        api_url: The DataCite base URL to call the API with.
        client_id: The DataCite API client id that will be used to query DataCite DOIs.
        endpoint: The endpoint to call the API with.
    """
    return get_url_json(f"{api_url}{endpoint}/{client_id}")


def extract_dois(datacite_response: dict) -> list:
    """
    Extract DOIs from a DataCite API data response object.

    For more information about the expected DataCite data response object see
    DataCite API documentation: https://support.datacite.org/reference/get_dois

    Args:
        datacite_response: DataCite API data response object.
    """
    data = datacite_response.get("data", [])
    dois = []

    for obj in data:
        if doi := obj.get("attributes", {}).get("doi"):
            dois.append(doi)

    return dois


def get_datacite_list_dois(
    api_url: str,
    client_id: str | None = None,
    doi_prefix: tuple[str, ...] = (),
    endpoint: str = DATACITE_API_DOIS_ENDPOINT,
) -> []:
    """
    Return a list of DOIs from DataCite API.
    Raises error if an unsuccessful response from DataCite API is returned
     or validation fails.

    For DataCite API documentation used in this call see
    https://support.datacite.org/reference/get_dois
    https://support.datacite.org/docs/pagination#method-2-cursor

    Supports the following query params from DataCite: "prefix", "client-id"

    Args:
        api_url: The DataCite base URL to call the API with.
        endpoint: The endpoint to call the API with.
        client_id: The DataCite API client id used to query DataCite DOIs.
        doi_prefix: The DOI prefixes used to query DataCite DOIs.
    """
    url = f"{api_url}{endpoint}"

    params = {}
    if doi_prefix:
        params["prefix"] = ",".join(doi_prefix)
    if client_id:
        params["client-id"] = client_id
    params["page[cursor]"] = 1
    params["page[size"] = 300  # TODO make a constant probably set at 1000

    pages = 1
    dois = []

    # Extract DOIs for first page
    resp_obj = get_url_json(url, params=params, timeout=TIMEOUT)
    if resp_dois := extract_dois(resp_obj):
        dois.extend(resp_dois)

    # Extract DOIs for subsequent pages
    while True:
        # Get next link using cursor-based pagination
        next_link = resp_obj.get("links", {}).get("next")
        if not next_link:
            break

        resp_obj = get_url_json(next_link, timeout=TIMEOUT)
        if resp_dois := extract_dois(resp_obj):
            dois.extend(resp_dois)

        pages += 1

    # Validate processed output matches number of DOIs and pages
    # in response "meta" object
    total_pages = resp_obj.get("meta", {}).get("totalPages")
    if total_pages != pages:
        raise APIError(
            f"Pages retrieved ({pages}) does not match the total number of pages "
            f"expected in response 'meta' object: {total_pages}, for DataCite API call"
            f"see {next_link}"
        )

    total_dois = resp_obj.get("meta", {}).get("total")
    dois_length = len(dois)
    if total_dois != dois_length:
        raise APIError(
            f"Total DOIs retrieved ({dois_length}) does not match the total number of "
            f"records expected in 'meta' object: {total_dois}, for DataCite API call"
            f"see {next_link}"
        )

    # TODO remove
    click.echo(f"pages: {pages}")
    click.echo(f"dois_length: {dois_length}")

    return dois
