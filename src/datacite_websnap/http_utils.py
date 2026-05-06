"""
Generic HTTP utility functions.
"""

from pathlib import Path
from typing import Any

import requests

from .config import TIMEOUT
from .logger import CustomClickException, CustomWarning


def get_url_json(
    url: str,
    params: dict | None = None,
    timeout: int = TIMEOUT,
) -> Any:
    """
    Return the JSON encoded part of a response if it exists as a Python object.
    Only supports GET requests.

    Args:
        url: The URL to call return the JSON response from.
        params: An optional dictionary of query parameters to send to the URL.
        timeout: Timeout of request in seconds.
    """
    try:
        response = requests.get(url, timeout=timeout, params=params)
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
            CustomWarning(f"401 Unauthorized for URL '{url}': {http_err}")
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


# TODO test
def get_url_content_stream(url: str, file_path: Path, timeout: int = TIMEOUT) -> None:
    """
    Stream content from url and write directly to file_path.

    Args:
        url: URL to download content from
        file_path: local path to write the content to
        timeout: timeout of request in seconds
    """
    try:
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

    except requests.exceptions.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 401:
            CustomWarning(f"401 Unauthorized for URL '{url}': {http_err}")
            return
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
