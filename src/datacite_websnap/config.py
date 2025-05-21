"""Configuration values for datacite-websnap (with environment variable support)."""

import os

# Timeout used for DataCite API and AWS requests
TIMEOUT: int = int(os.getenv("TIMEOUT", 32))

# DataCite API host, endpoints, and page size
DATACITE_API_URL: str = os.getenv("DATACITE_API_URL", "https://api.datacite.org")
DATACITE_API_CLIENTS_ENDPOINT: str = os.getenv(
    "DATACITE_API_CLIENTS_ENDPOINT", "/clients"
)
DATACITE_API_DOIS_ENDPOINT: str = os.getenv("DATACITE_API_DOIS_ENDPOINT", "/dois")
DATACITE_PAGE_SIZE: int = int(os.getenv("DATACITE_PAGE_SIZE", 250))

# Log name, format, and date format
LOG_NAME: str = os.getenv("LOG_NAME", "datacite-websnap.log")
LOG_FORMAT: str = os.getenv(
    "LOG_FORMAT",
    "%(asctime)s | %(levelname)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s",
)
LOG_DATE_FORMAT: str = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
