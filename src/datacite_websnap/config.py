"""Configuration values for datacite-websnap (with environment variable support)."""

# Timeout used for DataCite API and AWS requests
TIMEOUT: int = 32

# DataCite API host, endpoints, and page size
DATACITE_API_URL: str = "https://api.datacite.org"
DATACITE_API_CLIENTS_ENDPOINT: str = "/clients"
DATACITE_API_DOIS_ENDPOINT: str = "/dois"
DATACITE_PAGE_SIZE: int = 250

# Log name, format, and date format
LOG_NAME: str = "datacite-websnap.log"
LOG_FORMAT: str = (
    "%(asctime)s | %(levelname)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s"
)
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
