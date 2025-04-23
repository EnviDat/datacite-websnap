"""Logging configuration and utilities for datacite-websnap"""

import click
import logging

from .config import LOG_FORMAT, LOG_DATE_FORMAT, LOG_NAME


def setup_logging(log_level: str = "INFO"):
    """Set up the logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[logging.FileHandler(LOG_NAME)],
    )


def _log_error(message):
    """Log the error message."""
    logging.error(message, stacklevel=3)


class CustomClickException(click.ClickException):
    """Custom ClickException that conditionally logs exceptions."""

    def __init__(self, message: str, file_logs: bool = False):
        """
        Custom exception that logs formatted ClickExceptions to a log if
        file_logs is True.

        Args:
            message: Error message to display.
            file_logs: Flag to that enables logging exceptions to a log.
                         Default is False (logs are not enabled.)
        """
        super().__init__(message)
        self.file_logs = file_logs

        if self.file_logs:
            _log_error(message)

    def format_message(self) -> str:
        return click.style(super().format_message(), fg="red")


class CustomBadParameter(click.BadParameter):
    """Custom BadParameter exception that conditionally logs BadParameter exceptions."""

    def __init__(self, message: str, file_logs: bool = False):
        """
        Custom BadParameter exception that conditionally logs BadParameter exceptions
        to a log if file_logs is True.

        Args:
            message: Error message to display.
            file_logs: Flag to that enables logging exceptions to a log.
                         Default is False (logs are not enabled.)
        """
        super().__init__(message)
        self.file_logs = file_logs

        if self.file_logs:
            _log_error(message)

    def format_message(self) -> str:
        return click.style(super().format_message(), fg="red")


class CustomEcho:
    """Custom Echo that conditionally logs echo statements."""

    def __init__(self, message: str, file_logs: bool = False):
        """
        Custom echo class that conditionally logs echo statements to a log if
        file_logs is True.

        Args:
            message: Message to display.
            file_logs: Flag to that enables logging echo statements to a file log.
                       Default is False (logs are not enabled.)
        """
        click.echo(message)
        self.file_logs = file_logs

        if self.file_logs:
            self._log_info(message)

    @staticmethod
    def _log_info(message):
        """Log the 'INFO' message to the log file."""
        logging.info(message, stacklevel=3)


class CustomWarning:
    """Custom stylized echo class that conditionally logs warning statements."""

    def __init__(self, message: str, file_logs: bool = False):
        """
        Custom stylized echo class that conditionally logs warning statements to a log
        if file_logs is True.

        Args:
            message: Message to display.
            file_logs: Flag to that enables logging warning statements to a file log.
                       Default is False (logs are not enabled.)
        """
        click.secho(f"WARNING: {message}", fg="yellow", err=True)
        self.file_logs = file_logs

    @staticmethod
    def _log_warning(message):
        """Log the 'WARNING' message to the log file."""
        logging.warning(message, stacklevel=3)
