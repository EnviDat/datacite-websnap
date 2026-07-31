"""
Repository module for fetching and processing data from the PSI SciCat portal.
"""

from pydantic import ValidationError

from datacite_websnap.exporter import write_local_file_data_links
from datacite_websnap.logger import CustomClickException, custom_warning
from datacite_websnap.models import SciCatDoiResponse
from datetime import datetime, timezone


def _validate_scicat_doi_response(raw: dict) -> SciCatDoiResponse:
    try:
        return SciCatDoiResponse.model_validate(raw)
    except ValidationError as err:
        raise CustomClickException(
            f"Unexpected response format from PSI SciCat: {err}"
        ) from err


def _parse_scicat_data_urls(scicat_json: dict) -> dict:
    """
    Return a dictionary of PSI SciCat portal data file URL downloadable data files for a
    particular DOI.
    The dictionary is in the following format with the values extracted from the input
    scicat_json for each data file:
            {<contentUrl>: <expires>}

    Args:
        scicat_json: JSON response from PSI SciCat for a particular DOI
                     (as a Python dictionary)
    """
    urls_expires = {}

    validated_resp = _validate_scicat_doi_response(scicat_json)

    distribution = validated_resp.distribution
    for item in distribution:
        if item.expires:
            if item.name == "S3 URI":
                continue
            else:
                urls_expires[item.contentUrl] = item.expires

    return urls_expires


def _is_expired(date_str: str) -> bool:
    """
    Validate that a given ISO 8601 date string is before the current time.

    Accepts timestamps like:
        "2026-05-31T02:49:55Z"
        "2026-08-03T14:53:17.612Z"

    Returns True if the date is in the past, False otherwise.
    """
    # Python's fromisoformat doesn't accept trailing 'Z' before 3.11,
    # so normalize it to '+00:00' for broad compatibility.
    normalized = date_str.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as e:
        raise ValueError(f"Invalid ISO 8601 date string: {date_str!r}") from e

    # If the parsed datetime has no timezone info, assume UTC
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    return parsed < now


def extract_scicat_data_urls(scicat_json: dict) -> list[str]:
    """
    Extract valid SciCat data file URL links.
    They must not have a date for the "expires" field that is expired.

    Args:
       scicat_json: JSON response from PSI SciCat for a particular DOI
                     (as a Python dictionary)
    """
    urls_expire = _parse_scicat_data_urls(scicat_json)
    valid_urls = []

    # Extract valid URLs that are not expired
    for url in urls_expire:
        is_expired = True  # Assume date is expired until checked

        try:
            is_expired = _is_expired(urls_expire[url])
        except ValueError:
            custom_warning(
                f"Could not parse the date '{urls_expire[url]}' from the PSI SciCat "
                f"data file with URL '{url}'. "
                f"Please contact project administrator."
            )
        else:
            if is_expired:
                custom_warning(
                    f"Please refer to datacite-websnap documentation for "
                    f"accessing PSI Scicat files. "
                    f"Cannot download the following data file "
                    f"because it has an access date that "
                    f"has expired ('{urls_expire[url]}'): {url}"
                )

        if not is_expired:
            valid_urls.append(url)

    return valid_urls


def write_local_scicat_data_urls(
    scicat_json: dict, doi_directory: str, doi_prefix: str
) -> None:
    """
    Write SciCat data file URL links locally.

     Args:
        scicat_json: JSON response from PSI SciCat for a particular DOI
                     (as a Python dictionary)
        doi_directory: local path to directory to write the file in
        doi_prefix: prefix of the DOI
    """
    valid_urls = extract_scicat_data_urls(scicat_json)

    # Write locally data links using validated URLs
    for link in valid_urls:
        write_local_file_data_links(link, doi_directory, doi_prefix)

    return
