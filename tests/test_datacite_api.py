"""Tests for src/datacite-websnap/datacite_api.py"""

import pytest
from unittest.mock import patch

from datacite_websnap.datacite_api import (
    get_datacite_client,
    get_datacite_dois,
    get_datacite_doi,
    validate_doi_eth_standard,
    extract_doi_xml,
    get_datacite_list_dois_xml,
    CustomClickException,
)
from datacite_websnap.models import DoisResponse


def test_get_datacite_dois_pagination_params():
    with patch("datacite_websnap.datacite_api.get_url_json") as mock_get_url_json:
        mock_get_url_json.return_value = {"data": [], "meta": {}, "links": {}}

        get_datacite_dois(
            api_url="https://api.example.org",
            client_id="test-client",
            doi_prefix=("10.123",),
            page_size=100,
        )

        _, kwargs = mock_get_url_json.call_args
        params = kwargs["params"]
        assert "page[size]" in params
        assert params["page[size]"] == 100
        assert "page[cursor]" in params


def test_get_datacite_client():
    with patch("datacite_websnap.datacite_api.get_url_json") as mock_get:
        mock_get.return_value = {"client": "data"}
        result = get_datacite_client("https://api.example.org", "client123")
        assert result == {"client": "data"}


def test_get_datacite_doi_invalid_response_format():
    with patch(
        "datacite_websnap.datacite_api.get_url_json",
        return_value={"unexpected": "shape"},
    ):
        with pytest.raises(CustomClickException, match="Unexpected response format"):
            get_datacite_doi("https://api.example.org", "10.16904/abc")


def test_get_datacite_doi_success():
    raw = {"data": {"attributes": {"doi": "10.16904/abc", "xml": "base64xml"}}}
    with patch("datacite_websnap.datacite_api.get_url_json", return_value=raw):
        json_resp, xml, data_links = get_datacite_doi(
            "https://api.example.org", "10.16904/abc"
        )
        assert xml == "base64xml"
        assert data_links == []
        assert json_resp == raw


def test_get_datacite_doi_none_xml_raises():
    raw = {"data": {"attributes": {"doi": "10.16904/abc", "xml": None}}}
    with patch("datacite_websnap.datacite_api.get_url_json", return_value=raw):
        with pytest.raises(
            CustomClickException, match="does not have an associated XML"
        ):
            get_datacite_doi("https://api.example.org", "10.16904/abc")


def test_get_datacite_doi_url_construction():
    raw = {"data": {"attributes": {"doi": "10.16904/abc", "xml": "base64xml"}}}
    with patch(
        "datacite_websnap.datacite_api.get_url_json", return_value=raw
    ) as mock_get:
        get_datacite_doi("https://api.example.org", "10.16904/abc")
        mock_get.assert_called_once_with(
            url="https://api.example.org/dois/10.16904/abc"
        )


def test_validate_doi_eth_standard_valid():
    with patch(
        "datacite_websnap.datacite_api.validate.validate_datacite_from_string",
        return_value=(True, None),
    ):
        validate_doi_eth_standard(b"<xml/>", "10.123/test")


def test_validate_doi_eth_standard_invalid():
    with patch(
        "datacite_websnap.datacite_api.validate.validate_datacite_from_string",
        return_value=(False, None),
    ):
        with pytest.raises(
            CustomClickException, match="ETH metadata standard validation"
        ):
            validate_doi_eth_standard(b"<xml/>", "10.123/test")


def test_validate_doi_eth_standard_with_warnings():
    with patch(
        "datacite_websnap.datacite_api.validate.validate_datacite_from_string",
        return_value=(True, ["missing recommended field", "invalid date format"]),
    ):
        with patch("datacite_websnap.datacite_api.custom_warning") as mock_warning:
            validate_doi_eth_standard(b"<xml/>", "10.123/test")
            assert mock_warning.call_count == 2


def test_validate_doi_eth_standard_noncompliant():
    with patch(
        "datacite_websnap.datacite_api.validate.validate_datacite_from_string",
        return_value=(False, ["missing required field"]),
    ):
        with patch("datacite_websnap.datacite_api.custom_warning") as mock_warning:
            with pytest.raises(
                CustomClickException, match="ETH metadata standard validation"
            ):
                validate_doi_eth_standard(b"<xml/>", "10.123/test")
            assert mock_warning.call_count == 1


def test_get_datacite_doi_data_links():
    raw = {
        "data": {
            "attributes": {
                "doi": "10.16904/abc",
                "xml": "base64xml",
                "relatedItems": [
                    {
                        "relatedItemType": "Other",
                        "relationType": "References",
                        "relatedItemIdentifier": {
                            "relatedItemIdentifier": "https://example.com/data.csv",
                            "relatedItemIdentifierType": "URL",
                        },
                    }
                ],
            }
        }
    }
    with patch("datacite_websnap.datacite_api.get_url_json", return_value=raw):
        _, _, data_links = get_datacite_doi("https://api.example.org", "10.16904/abc")
        assert data_links == ["https://example.com/data.csv"]


def test_get_datacite_doi_data_links_filtered():
    """Items that don't match type/relation/identifierType are excluded."""
    raw = {
        "data": {
            "attributes": {
                "doi": "10.16904/abc",
                "xml": "base64xml",
                "relatedItems": [
                    {
                        "relatedItemType": "JournalArticle",
                        "relationType": "References",
                        "relatedItemIdentifier": {
                            "relatedItemIdentifier": "https://example.com/paper",
                            "relatedItemIdentifierType": "URL",
                        },
                    }
                ],
            }
        }
    }
    with patch("datacite_websnap.datacite_api.get_url_json", return_value=raw):
        _, _, data_links = get_datacite_doi("https://api.example.org", "10.16904/abc")
        assert data_links == []


def test_extract_doi_xml_valid():
    resp = DoisResponse.model_validate(
        {
            "data": [
                {"attributes": {"doi": "10.123/abc", "xml": "<xml1>"}},
                {"attributes": {"doi": "10.123/def", "xml": "<xml2>"}},
            ],
            "meta": {"total": 2, "totalPages": 1},
            "links": {},
        }
    )
    doi_xml, skipped = extract_doi_xml(resp)
    assert doi_xml == [{"10.123/abc": "<xml1>"}, {"10.123/def": "<xml2>"}]
    assert skipped == []


def test_extract_doi_xml_missing_xml():
    resp = DoisResponse.model_validate(
        {
            "data": [{"attributes": {"doi": "10.123/abc"}}],
            "meta": {"total": 1, "totalPages": 1},
            "links": {},
        }
    )
    doi_xml, skipped = extract_doi_xml(resp)
    assert doi_xml == []
    assert skipped == ["10.123/abc"]


def test_get_datacite_list_dois_xml_invalid_response():
    with patch(
        "datacite_websnap.datacite_api.get_datacite_dois",
        return_value={"unexpected": "shape"},
    ):
        with pytest.raises(CustomClickException, match="Unexpected response format"):
            get_datacite_list_dois_xml(
                api_url="https://api.example.org", client_id="test-client"
            )


def test_get_datacite_list_dois_xml_single_page():
    mock_response = {
        "meta": {"total": 2, "totalPages": 1},
        "links": {},
        "data": [
            {"attributes": {"doi": "10.123/abc", "xml": "<xml1>"}},
            {"attributes": {"doi": "10.123/def", "xml": "<xml2>"}},
        ],
    }

    with patch(
        "datacite_websnap.datacite_api.get_url_json", return_value=mock_response
    ):
        with patch("datacite_websnap.datacite_api.custom_echo"):
            results = get_datacite_list_dois_xml(
                api_url="https://api.example.org",
                client_id="client123",
                doi_prefix=("abc", "def"),
            )
            assert len(results) == 2
            assert {"10.123/abc": "<xml1>"} in results


def test_get_datacite_list_dois_xml_zero_records():
    mock_response = {
        "meta": {"total": 0, "totalPages": 1},
        "links": {},
        "data": [],
    }

    with patch(
        "datacite_websnap.datacite_api.get_url_json",
        return_value=mock_response,
    ):
        with pytest.raises(CustomClickException):
            get_datacite_list_dois_xml(
                api_url="https://api.example.org", client_id="test-client"
            )


def test_get_datacite_list_dois_xml_multiple_pages():
    first_page = {
        "meta": {"total": 4, "totalPages": 2},
        "links": {"next": "https://next.page"},
        "data": [
            {"attributes": {"doi": "10.123/abc", "xml": "<xml1>"}},
            {"attributes": {"doi": "10.123/def", "xml": "<xml2>"}},
        ],
    }

    second_page = {
        "meta": {"total": 4, "totalPages": 2},
        "links": {},
        "data": [
            {"attributes": {"doi": "10.123/ghi", "xml": "<xml3>"}},
            {"attributes": {"doi": "10.123/jkl", "xml": "<xml4>"}},
        ],
    }

    with patch(
        "datacite_websnap.datacite_api.get_url_json",
        side_effect=[first_page, second_page],
    ) as mock_get:
        with patch("datacite_websnap.datacite_api.custom_echo"):
            result = get_datacite_list_dois_xml(
                api_url="https://api.example.org",
                client_id="test-client",
                page_size=100,
            )

    expected = [
        {"10.123/abc": "<xml1>"},
        {"10.123/def": "<xml2>"},
        {"10.123/ghi": "<xml3>"},
        {"10.123/jkl": "<xml4>"},
    ]

    assert result == expected

    # Verify page[size] is forwarded on the second-page request
    _, second_call_kwargs = mock_get.call_args_list[1]
    assert second_call_kwargs["params"]["page[size]"] == 100


def test_get_datacite_list_dois_xml_mismatched_total_records():
    first_page = {
        "meta": {"total": 3, "totalPages": 1},
        "links": {},
        "data": [
            {"attributes": {"doi": "10.123/abc", "xml": "<xml1>"}},
            {"attributes": {"doi": "10.123/def", "xml": "<xml2>"}},
        ],
    }

    with patch("datacite_websnap.datacite_api.get_url_json", return_value=first_page):
        with patch("datacite_websnap.datacite_api.custom_echo"):
            with patch("datacite_websnap.datacite_api.custom_warning") as mock_warning:
                result = get_datacite_list_dois_xml(
                    api_url="https://api.example.org", client_id="test-client"
                )

    mock_warning.assert_called_once()
    assert "3" in mock_warning.call_args[0][0]
    assert result == [{"10.123/abc": "<xml1>"}, {"10.123/def": "<xml2>"}]


def test_get_datacite_list_dois_xml_skips_null_xml_with_warning():
    mock_response = {
        "meta": {"total": 3, "totalPages": 1},
        "links": {},
        "data": [
            {"attributes": {"doi": "10.123/abc", "xml": "<xml1>"}},
            {"attributes": {"doi": "10.123/no-xml"}},
            {"attributes": {"doi": "10.123/def", "xml": "<xml2>"}},
        ],
    }

    with patch(
        "datacite_websnap.datacite_api.get_url_json", return_value=mock_response
    ):
        with patch("datacite_websnap.datacite_api.custom_echo"):
            with patch("datacite_websnap.datacite_api.custom_warning") as mock_warning:
                result = get_datacite_list_dois_xml(
                    api_url="https://api.example.org", client_id="test-client"
                )

    assert result == [{"10.123/abc": "<xml1>"}, {"10.123/def": "<xml2>"}]
    mock_warning.assert_called_once()
    assert "10.123/no-xml" in mock_warning.call_args[0][0]
