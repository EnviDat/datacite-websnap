"""Logging configuration and utilities for datacite-websnap"""

import click
import logging

from .config import LOG_FORMAT, LOG_DATE_FORMAT, LOG_NAME


def _has_file_handler() -> bool:
    return any(isinstance(h, logging.FileHandler) for h in logging.getLogger().handlers)


def setup_logging(log_level: str = "INFO", file_logs: bool = False):
    """Set up the logging configuration."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level, logging.INFO))
    if file_logs and not _has_file_handler():
        handler = logging.FileHandler(LOG_NAME)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        root.addHandler(handler)


class CustomClickException(click.ClickException):
    """Custom ClickException that conditionally logs exceptions."""

    def __init__(self, message: str):
        """
        Custom exception that logs formatted ClickExceptions
        if --file-log option has been enabled and FileHandler setup.

        Args:
            message: Error message to display.
        """
        super().__init__(message)

    @staticmethod
    def _log_error(message):
        """Log the error message."""
        logging.error(message)

    def format_message(self) -> str:
        return click.style(super().format_message(), fg="red")

    def show(self, file=None):
        if _has_file_handler():
            self._log_error(self.message)

        click.echo(f"ERROR: {self.format_message()}", err=True)


class CustomBadParameter(click.BadParameter):
    """Custom BadParameter exception that conditionally logs BadParameter exceptions."""

    def __init__(self, message: str):
        """
        Custom BadParameter exception that styles console message.

        Args:
            message: Error message to display.
        """
        super().__init__(message)

    def format_message(self) -> str:
        return click.style(super().format_message(), fg="red")


class CustomEcho:
    """Custom Echo that conditionally logs echo statements."""

    def __init__(self, message: str):
        """
        Custom echo class that conditionally logs echo statements to a log
        if --file-log option has been enabled and FileHandler setup.

        Args:
            message: Message to display.
        """
        click.echo(message)

        if _has_file_handler():
            self._log_info(message)

    @staticmethod
    def _log_info(message):
        """Log the 'INFO' message."""
        logging.info(message)


class CustomWarning:
    """
    Custom stylized echo class that conditionally logs warning statements
    if --file-log option has been enabled and FileHandler setup.
    """

    def __init__(self, message: str):
        """
        Args:
            message: Message to display.
        """
        click.secho(f"WARNING: {message}", fg="yellow", err=True)

        if _has_file_handler():
            self._log_warning(message)

    @staticmethod
    def _log_warning(message):
        """Log the 'WARNING' message to the log file."""
        logging.warning(message)
