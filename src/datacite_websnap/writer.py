"""
Process and write DataCite XML files.
"""

import base64
import os

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
            root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        ).decode("utf-8")

    except UnicodeDecodeError:
        raise click.ClickException("UnicodeDecode Error: Unable to decode XML")

    except etree.XMLSyntaxError as syntax_err:
        raise click.ClickException(
            f"XMLSyntax Error: Unable to decode XML: {syntax_err}"
        )

    except Exception as err:
        raise click.ClickException(f"Unexpected error: {err}")


def format_xml_file_name(doi: str) -> str:
    """
    Format "doi" value into an XML filename.
    "/" replaced with "_" and ".xml" appended to the filename.

    Example input: "10.16904/envidat.31"
    Example output: "10.16904_envidat.31.xml"

    Args:
        doi: "doi" string, example "10.16904/envidat.31"
    """
    doi_format = doi.replace("/", "_")
    return f"{doi_format}.xml"


def write_file(content_str: str, filename: str, directory_path: str | None = None):
    """
    Write a string to a file.
    """
    try:
        if directory_path:
            file_path = os.path.join(directory_path, filename)
        else:
            file_path = filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content_str)

        click.echo(f"Wrote file: {file_path}")

    except IOError as io_err:
        raise click.ClickException(f"IOError: {io_err}")

    except Exception as err:
        raise click.ClickException(f"Unexpected error: {err}")
