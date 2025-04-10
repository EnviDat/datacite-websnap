"""
Process and write DataCite XML files.
"""

import base64
import click
from lxml import etree


def decode_base64_xml(encoded_xml: str) -> str:
    """
    Decodes a Base64-encoded XML string and returns it as a
    pretty-print formatted XML string.

    Args:
        encoded_xml: Base64-encoded XML string.
    """
    try:
        decoded_bytes = base64.b64decode(encoded_xml)
        root = etree.fromstring(decoded_bytes)

        return etree.tostring(
            root, pretty_print=True, encoding="utf-8", xml_declaration=True
        ).decode("utf-8")

    except UnicodeDecodeError:
        raise click.ClickException("UnicodeDecode Error: Unable to decode XML")

    except etree.XMLSyntaxError as syntax_err:
        raise click.ClickException(
            f"XMLSyntax Error: Unable to decode XML: {syntax_err}"
        )

    except Exception as err:
        raise click.ClickException(f"Unexpected error: {err}")


# TODO remove
def decode_base64_xml_to_bytes(encoded_xml: str) -> bytes:
    """
    Decodes a Base64-encoded XML string and returns it as bytes.

    Args:
        encoded_xml: Base64-encoded XML string.
    """
    try:
        return base64.b64decode(encoded_xml)
    except UnicodeDecodeError:
        print("Error: Unable to decode XML bytes as UTF-8.")
    except etree.XMLSyntaxError as e:
        print(f"XML parse error: {e}")
    except Exception as e:
        print(f"Unexpected error during XML processing: {e}")
