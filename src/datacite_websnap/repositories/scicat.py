"""
Repository module for fetching and processing data from the PSI Sciat portal.
"""

from botocore.exceptions import ValidationError
from datacite_websnap.logger import CustomClickException
from datacite_websnap.models import SciCatDoiResponse
from datacite_websnap.http_utils import get_url_content_length_stream


def _validate_scicat_doi_response(raw: dict) -> SciCatDoiResponse:
    try:
        return SciCatDoiResponse.model_validate(raw)
    except ValidationError as err:
        raise CustomClickException(
            f"Unexpected response format from PSI SciCat: {err}"
        ) from err


def _parse_scicat_data_urls(scicat_json: dict) -> list[str]:
    """
    Return a list of PSI SciCat portal data file URL downloadable data files for a
    particular DOI.

    Args:
        scicat_json: JSON reponse from PSI SciCat for a particualr DOI
                     (as a Python dictionary)
    """
    data_urls = []

    validated_resp = _validate_scicat_doi_response(scicat_json)

    distribution = validated_resp.distribution
    for item in distribution:
        if item.name != "S3 URI":
            data_urls.append(item.contentUrl)

    return data_urls


# TODO modify to write to S3
def write_scicat_data_urls(scicat_json: dict) -> None:
    """
    Write SciCat data urls locally.

     Args:
        scicat_json: JSON reponse from PSI SciCat for a particualr DOI
                     (as a Python dictionary)
    """
    data_urls = _parse_scicat_data_urls(scicat_json)
    for url in data_urls:
        content = get_url_content_length_stream(url)
        print(content)
