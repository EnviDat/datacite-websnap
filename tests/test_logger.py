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
            raise CustomClickException("Something went wrong", file_logs=True)

        assert "Something went wrong" in caplog.text


def test_custom_click_exception_format_message():
    exc = CustomClickException("Oops", file_logs=False)
    assert "Oops" in exc.format_message()


def test_custom_bad_parameter_logs_error(caplog):
    with caplog.at_level(logging.ERROR):
        with pytest.raises(CustomBadParameter):
            raise CustomBadParameter("Invalid input", file_logs=True)

        assert "Invalid input" in caplog.text


def test_custom_bad_parameter_format_message():
    exc = CustomBadParameter("Bad param", file_logs=False)
    assert "Bad param" in exc.format_message()


def test_custom_echo_logs_info(caplog):
    with caplog.at_level(logging.INFO):
        CustomEcho("Hello world", file_logs=True)
        assert "Hello world" in caplog.text


def test_custom_echo_no_log(caplog):
    with caplog.at_level(logging.INFO):
        CustomEcho("Hello world", file_logs=False)
        assert "Hello world" not in caplog.text


def test_custom_warning_stdout(capsys):
    CustomWarning("Something might be wrong", file_logs=False)
    captured = capsys.readouterr()
    assert "WARNING: Something might be wrong" in captured.err


def test_custom_warning_log(caplog):
    with patch.object(logging, "warning") as mock_warning:
        warning = CustomWarning("Log this warning", file_logs=True)
        warning._log_warning("Log this warning")
        mock_warning.assert_called_with("Log this warning", stacklevel=3)
