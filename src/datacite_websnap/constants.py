"""Constants used by datacite-websnap."""

TIMEOUT: int = 32

DATACITE_API_URL: str = "https://api.datacite.org"
DATACITE_API_CLIENTS_ENDPOINT: str = "/clients"
DATACITE_API_DOIS_ENDPOINT: str = "/dois"
DATACITE_PAGE_SIZE: int = 250

LOG_NAME: str = "datacite-websnap.log"
LOG_FORMAT: str = (
    "%(asctime)s | %(levelname)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s"
)
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
