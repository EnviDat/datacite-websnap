"""
Generic HTTP utility functions.
"""

from typing import Any

import requests

from .config import TIMEOUT
from .logger import CustomClickException, custom_warning


def get_url_json(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = TIMEOUT,
) -> Any:
    """
    Return the JSON encoded part of a response if it exists as a Python object.
    Only supports GET requests.

    Args:
        url: The URL to call return the JSON response from.
        params: An optional dictionary of query parameters to send to the URL.
        headers: An optional dictionary of headers to send to the URL.
        timeout: Timeout of request in seconds.
    """
    try:
        response = requests.get(url, timeout=timeout, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        raise CustomClickException(f"HTTP error while calling URL '{url}': {http_err}")

    except requests.exceptions.JSONDecodeError:
        raise CustomClickException(
            f"Invalid response for URL '{url}': The server did not return valid JSON.",
        )

    except requests.exceptions.ConnectionError:
        raise CustomClickException(
            f"Network error for URL '{url}': Unable to connect to the API."
        )

    except requests.exceptions.Timeout:
        raise CustomClickException(
            f"Request timeout for URL '{url}': The API did not respond within "
            f"the timeout of {timeout} seconds."
        )

    except requests.exceptions.RequestException as req_err:
        raise CustomClickException(f"Request failed for URL '{url}': {req_err}")

    except Exception as err:
        raise CustomClickException(
            f"Unexpected error occurred while calling URL '{url}': {err}"
        ) from err


def get_url_content_length_stream(url: str, timeout: tuple[int, int] = (5, 10)) -> int:
    """
    Return the Content-Length of the resource at url via a GET request, or 0 if
    the header is absent or the request fails. Uses the "stream=True" parameter because
    some URLs are expected to not allow HEAD requests.

    Args:
        url: URL to send the GET request to.
        timeout: (connect_timeout, read_timeout) in seconds.
    """
    try:
        with requests.get(
            url, stream=True, timeout=timeout, allow_redirects=True
        ) as response:
            return int(response.headers.get("Content-Length", 0))
    except (requests.RequestException, ValueError):
        return 0


def get_url_content_length(url: str, timeout: tuple[int, int] = (5, 10)) -> int:
    """
    Return the Content-Length of the resource at url via a HEAD request, or 0 if
    the header is absent or the request fails.

    Args:
        url: URL to send the HEAD request to.
        timeout: (connect_timeout, read_timeout) in seconds.
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return int(response.headers.get("Content-Length", 0))
    except (requests.exceptions.RequestException, ValueError):
        return 0


def get_url_content(url: str, timeout: int = TIMEOUT) -> bytes | None:
    """
    Return the content of the given URL as a byte string.

    Args:
         url: The URL to call return the content from.
         timeout: Timeout of request in seconds.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content

    except requests.exceptions.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 401:
            custom_warning(f"401 Unauthorized for URL '{url}': {http_err}")
            return None
        raise CustomClickException(f"HTTP error while calling URL '{url}': {http_err}")

    except requests.exceptions.ConnectionError:
        raise CustomClickException(f"Network error for URL '{url}': Unable to connect.")

    except requests.exceptions.Timeout:
        raise CustomClickException(
            f"Request timeout for URL '{url}': No response within {timeout}s."
        )

    except requests.exceptions.RequestException as err:
        raise CustomClickException(f"Request failed for URL '{url}': {err}")

    except Exception as err:
        raise CustomClickException(
            f"Unexpected error occurred while calling URL '{url}': {err}"
        ) from err
