"""
DataCite API data retrieval, validation and processing.
"""

from typing import Any

import click
from pydantic import ValidationError
from validator import validate

from .config import (
    DATACITE_API_CLIENTS_ENDPOINT,
    TIMEOUT,
    DATACITE_API_DOIS_ENDPOINT,
    DATACITE_PAGE_SIZE,
)
from .http_utils import get_url_json
from .logger import CustomClickException, CustomEcho, CustomWarning
from .models import DoisResponse, SingleDoiResponse


def get_datacite_client(api_url: str, client_id: str) -> dict[str, Any]:
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
    return get_url_json(url=f"{api_url}{DATACITE_API_CLIENTS_ENDPOINT}/{client_id}")


def get_datacite_dois(
    api_url: str,
    client_id: str | None = None,
    doi_prefix: tuple[str, ...] = (),
    page_size: int = DATACITE_PAGE_SIZE,
) -> dict[str, Any]:
    """
    Returns a list of DOIs as a response from DataCite API.
    Uses cursor pages pagination to return the first page of the response.
    Raises error if response is not successful.

    For DataCite API documentation used in this call see
    https://support.datacite.org/reference/get_dois
    https://support.datacite.org/docs/pagination#method-2-cursor

    Args:
        api_url: The DataCite base URL to call the API with.
        client_id: The DataCite API client id used to query DataCite DOIs.
        doi_prefix: The DOI prefixes used to query DataCite DOIs.
        page_size: DataCite page size is the number of records
                   returned per page using pagination.
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
    params["page[size]"] = page_size

    # Get response for first page
    return get_url_json(url, params=params, timeout=TIMEOUT)


def _validate_dois_response(raw: dict) -> DoisResponse:
    try:
        return DoisResponse.model_validate(raw)
    except ValidationError as err:
        raise CustomClickException(
            f"Unexpected response format from DataCite API: {err}"
        ) from err


def extract_doi_xml(datacite_response: DoisResponse) -> list[dict]:
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
        datacite_response: Validated DataCite API data response object.
    """
    doi_xml = []

    for obj in datacite_response.data:
        if obj.attributes.xml is not None:
            doi_xml.append({obj.attributes.doi: obj.attributes.xml})

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

    Supports the following search query params from DataCite: "prefix", "client-id"

    Args:
        api_url: The DataCite base URL to call the API with.
        client_id: The DataCite API client id used to query DataCite DOIs.
        doi_prefix: The DOI prefixes used to query DataCite DOIs.
        page_size: DataCite page size is the number of records
                   returned per page using pagination.
    """
    # Get and validate response for first page
    resp = _validate_dois_response(
        get_datacite_dois(api_url, client_id, doi_prefix, page_size)
    )

    # Echo total number of returned DOIs
    total_records = resp.meta.total
    CustomEcho(
        f"Total number of DataCite DOIs returned for search query: {total_records}"
    )

    # Handle 0 records returned
    if total_records == 0:
        raise CustomClickException(
            "0 records returned for search query, review '--client-id' and/or "
            "'--doi-prefix' arguments"
        )

    # Echo DOIs per page
    CustomEcho(f"Number of DOIs per page: {page_size}")

    # Echo page being currently processed
    pages = 1
    total_pages = resp.meta.totalPages
    CustomEcho(f"Currently processing page {pages}/{total_pages}...")

    # Extract DOIs and XML strings for first page
    xml_lst = []
    if resp_xml_lst := extract_doi_xml(resp):
        xml_lst.extend(resp_xml_lst)

    # Extract DOIs and XML strings for subsequent pages
    while True:
        if pages < total_pages:
            CustomEcho(f"Currently processing page {pages + 1}/{total_pages}...")

        # Get next link using cursor-based pagination
        next_link = resp.links.next
        if not next_link:
            break

        resp = _validate_dois_response(
            get_url_json(next_link, params={"detail": "true"}, timeout=TIMEOUT)
        )
        if resp_xml_lst := extract_doi_xml(resp):
            xml_lst.extend(resp_xml_lst)

        pages += 1

    # Validate processed output matches number of records in response "meta" object
    xml_lst_length = len(xml_lst)
    if total_records != xml_lst_length:
        raise CustomClickException(
            f"Total number of XML records retrieved ({xml_lst_length}) does not match "
            f"the total number of records expected in 'meta' object: {total_records}"
        )

    return xml_lst


def _validate_single_doi_response(raw: dict) -> SingleDoiResponse:
    try:
        return SingleDoiResponse.model_validate(raw)
    except ValidationError as err:
        raise CustomClickException(
            f"Unexpected response format from DataCite API: {err}"
        ) from err


def get_datacite_doi(api_url: str, doi: str) -> tuple[Any, str, list[str]]:
    """
    Return a DataCite API DOI JSON response, "xml" value (in encoded format),
    and list of links to data files.

    Raises error if DOI does not return a successful response from the
    DataCite API.

    For DataCite API documentation used in this call see
    https://support.datacite.org/reference/get_dois-id

    Args:
        api_url: The DataCite base URL to call the API with.
        doi: The DOI that will be used to query DataCite DOIs.
    """
    json_resp = get_url_json(url=f"{api_url}{DATACITE_API_DOIS_ENDPOINT}/{doi}")

    validated_resp = _validate_single_doi_response(json_resp)

    xml_encoded = validated_resp.data.attributes.xml
    if xml_encoded is None:
        raise CustomClickException(
            f"DOI '{doi}' does not have an associated XML metadata record."
        )

    data_links = []
    related_items = validated_resp.data.attributes.relatedItems or []
    for item in related_items:
        if (
            item.relatedItemType == "Other"
            and item.relationType == "References"
            and item.relatedItemIdentifier
            and item.relatedItemIdentifier.relatedItemIdentifierType == "URL"
            and item.relatedItemIdentifier.relatedItemIdentifier
        ):
            data_links.append(item.relatedItemIdentifier.relatedItemIdentifier)

    return json_resp, xml_encoded, data_links


# TODO test with a non-compliant DOI
def validate_doi_eth_standard(xml_decoded: bytes) -> None:
    """
    Validate DataCite DOI XML value is compliant with ETH metadata standard.
    Logs warnings regarding recommended values in DOI
    in alignment with ETH metadata standard.

    Raises error if validation fails.

    To learn more about the ETH metadata standard please refer to:
    https://www.dora.lib4ri.ch/psi/dload/psi:81336/PDF/Felder-2025-Recommendation_on_how_to_implement-(published_version).pdf

    To learn more about the validation function used please refer to:
    https://pypi.org/project/eth-datacite-validator/

    Args:
        xml_decoded: DataCite DOI XML string in decoded format
    """
    is_record_valid, warnings = validate.validate_datacite_from_string(
        xml_decoded=xml_decoded, give_warning=True, result_only=False
    )

    if warnings:
        for warning in warnings:
            CustomWarning(warning)
        click.echo("")

    if not is_record_valid:
        raise CustomClickException(
            "DOI failed to pass ETH metadata standard validation."
        )
