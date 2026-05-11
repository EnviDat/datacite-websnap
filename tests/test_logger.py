"""Tests for src/datacite-websnap/logger.py"""

import logging
import pytest
from unittest.mock import patch

from datacite_websnap.logger import (
    CustomClickException,
    CustomBadParameter,
    CustomEcho,
    CustomWarning,
)


def test_custom_click_exception_logs_error(caplog):
    with caplog.at_level(logging.ERROR):
        with pytest.raises(CustomClickException):
            raise CustomClickException("Something went wrong")


def test_custom_click_exception_format_message():
    exc = CustomClickException("Oops")
    assert "Oops" in exc.format_message()


def test_custom_bad_parameter_logs_error(caplog):
    with caplog.at_level(logging.ERROR):
        with pytest.raises(CustomBadParameter):
            raise CustomBadParameter("Invalid input")


def test_custom_bad_parameter_format_message():
    exc = CustomBadParameter("Bad param")
    assert "Bad param" in exc.format_message()


def test_custom_echo_logs_info(caplog):
    with caplog.at_level(logging.INFO):
        CustomEcho("Hello world")
        assert "Hello world" in caplog.text


def test_custom_warning_stdout(capsys):
    CustomWarning("Something might be wrong")
    captured = capsys.readouterr()
    assert "WARNING: Something might be wrong" in captured.err


def test_custom_warning_log(caplog):
    with patch("datacite_websnap.logger._has_file_handler", return_value=True):
        with caplog.at_level(logging.WARNING):
            CustomWarning("Log this warning")
            assert "Log this warning" in caplog.text
