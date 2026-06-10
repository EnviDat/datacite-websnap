"""Tests for src/datacite-websnap/logger.py"""

import logging
import pytest
from unittest.mock import patch

from datacite_websnap.logger import (
    CustomClickException,
    CustomBadParameter,
    custom_echo,
    custom_warning,
)


def test_custom_click_exception_can_be_raised():
    with pytest.raises(CustomClickException, match="Something went wrong"):
        raise CustomClickException("Something went wrong")


def test_custom_click_exception_show_logs_when_file_handler(capsys):
    with patch("datacite_websnap.logger._has_file_handler", return_value=True):
        with patch("datacite_websnap.logger.logging.error") as mock_log:
            exc = CustomClickException("Something went wrong")
            exc.show()
            mock_log.assert_called_once_with("Something went wrong")
    assert "Something went wrong" in capsys.readouterr().err


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


def test_custom_echo_logs_info():
    with patch("datacite_websnap.logger._has_file_handler", return_value=True):
        with patch("datacite_websnap.logger.logging.info") as mock_log:
            custom_echo("Hello world")
            mock_log.assert_called_once_with("Hello world")


def test_custom_warning_stdout(capsys):
    custom_warning("Something might be wrong")
    captured = capsys.readouterr()
    assert "WARNING: Something might be wrong" in captured.err


def test_custom_warning_log(caplog):
    with patch("datacite_websnap.logger._has_file_handler", return_value=True):
        with caplog.at_level(logging.WARNING):
            custom_warning("Log this warning")
            assert "Log this warning" in caplog.text
