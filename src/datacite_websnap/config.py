"""Configuration values for datacite-websnap."""

# Timeout used for DataCite API and AWS requests
TIMEOUT: int = 32

# DataCite API host, endpoints, and page size
DATACITE_API_URL: str = "https://api.datacite.org"
DATACITE_API_CLIENTS_ENDPOINT: str = "/clients"
DATACITE_API_DOIS_ENDPOINT: str = "/dois"
DATACITE_PAGE_SIZE: int = 250

# Supported DOI prefixes for doi-export command
#   EnviDat prefix         -> 10.16904
#   SciCat (PSI) prefix    -> 10.16907
#   Materials Cloud prefix -> 10.24435
DATACITE_DOIS_PREFIXES: tuple[str, ...] = ("10.16904",)

# Log name, format, and date format
LOG_NAME: str = "datacite-websnap.log"
LOG_FORMAT: str = "%(asctime)s | %(levelname)s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# Threshold for switching from sequential to parallel data uploads
PARALLEL_UPLOAD_THRESHOLD: int = 10
