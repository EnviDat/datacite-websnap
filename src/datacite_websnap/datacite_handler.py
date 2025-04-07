"""
Handles interactions with DataCite API.
"""
import pprint

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
        click.echo(response.url)
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


# TODO WIP start dev here
def get_datacite_list_dois(
    api_url: str,
    client_id: str | None = None,
    doi_prefix: tuple[str, ...] = (),
    endpoint: str = DATACITE_API_DOIS_ENDPOINT,
):
    """
    Return a list of DOIs from DataCite API.
    Raises error if an unsuccessful response from DataCite API is returned.

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
    params["page[size"] = 100  # TODO make a constant probably set at 1000

    count = 0  # TODO remove

    # TODO fix this
    # while True:
    #
    #     data = get_url_json(url, params=params, timeout=TIMEOUT)
    #
    #     # TODO extract DOIs (from "id property), add to a list
    #
    #     # Get next link using cursor-based pagination
    #     next_link = data.get("links", {}).get("next")
    #     if not next_link:
    #         break
    #
    #     url = next_link
    #
    #     count += 1
    #     click.echo(f"{count}: {url}")






