"""
Handles interactions with DataCite API.
"""

import click
import requests

from .constants import DATACITE_API_CLIENTS_ENDPOINT, TIMEOUT


class APIError(click.ClickException):
    """Custom Click exception for API related errors."""
    def __init__(self, message):
        super().__init__(message)


def get_url_json(url: str, timeout: int = TIMEOUT):
    """
    Return the json encoded part of a response if it exists as a Python object.
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
        raise APIError("Request timeout: The API did not respond in time.")

    except requests.exceptions.RequestException as req_err:
        raise APIError(f"API request failed: {req_err}")

    except Exception as err:
        raise APIError(f"Unexpected error: {err}")


def get_datacite_client(
        api_url: str,
        client_id: str,
        endpoint: str = DATACITE_API_CLIENTS_ENDPOINT
):
    """
    Return client response from DataCite API.
    Raises error if client id does not return a successful response from the
    DataCite API.
    For DataCite API documentation used in this call see
    https://support.datacite.org/reference/get_clients-id
    """
    return get_url_json(f"{api_url}{endpoint}/{client_id}")
