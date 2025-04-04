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


def get_url_json(url: str, timeout: int = TIMEOUT):
    """
    Return the JSON encoded part of a response if it exists as a Python object.
    Only supports GET requests.

    Args:
        url: The URL to call return the JSON response from.
        timeout: Timeout of request in seconds.
    """
    try:
        response = requests.get(url, timeout=timeout)
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


# TODO implement support for cursor-based pagination,
#  see https://support.datacite.org/docs/pagination#method-2-cursor
# TODO WIP start dev here
def get_datacite_list_dois(
    api_url: str,
    endpoint: str = DATACITE_API_DOIS_ENDPOINT,
    client_id: str | None = None,
    doi_prefix: tuple[str, ...] = (),
):
    """
    Return a list of DOIs from DataCite API.
    Raises error if an unsuccessful response from DataCite API is returned.
    For DataCite API documentation used in this call see
    https://support.datacite.org/reference/get_dois
    Supports the following query params from DataCite: "prefix", "client-id"

    Args:
        api_url: The DataCite base URL to call the API with.
        endpoint: The endpoint to call the API with.
        client_id: The DataCite API client id used to query DataCite DOIs.
        doi_prefix: The DOI prefixes used to query DataCite DOIs.
    """
    pass
