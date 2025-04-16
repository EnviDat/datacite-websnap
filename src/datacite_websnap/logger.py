"""Logging configuration and utilities for datacite-websnap"""

import click
import logging

from .constants import LOG_FORMAT, LOG_DATE_FORMAT, LOG_NAME


# TODO implement CustomClickEcho
# TODO have functions call customized logging functions

# TODO possibly configure level, see websnap get_log_level()
def setup_logging():
    """Set up the logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[logging.FileHandler(LOG_NAME)],
    )


class CustomClickException(click.ClickException):
    """Custom ClickException that conditionally logs to a file."""

    def __init__(self, message: str, enable_logs: bool = False):
        """
        Custom exception that logs formatted ClickExceptions to file log if
        enable_logs is True.

        Args:
            message: Error message to display.
            enable_logs: Flag to that enables logging exceptions to a file log.
                         Default is False (logs are not enabled.)
        """
        super().__init__(message)
        self.enable_logs = enable_logs

        if self.enable_logs:
            self._log_error(message)

    @staticmethod
    def _log_error(message):
        """Log the error message to the log file with a timestamp."""
        logging.error(message, stacklevel=3)
