"""Configuration values for datacite-websnap."""

# Timeout used for DataCite API and AWS requests
TIMEOUT: int = 32

# DataCite API host, endpoints, and page size
DATACITE_API_URL: str = "https://api.datacite.org"
DATACITE_API_CLIENTS_ENDPOINT: str = "/clients"
DATACITE_API_DOIS_ENDPOINT: str = "/dois"
DATACITE_PAGE_SIZE: int = 250

# Supported DOI prefixes for doi-export command
#   EnviDat -> 10.16904
#   Materials Cloud -> 10.24435
DATACITE_DOIS_PREFIXES: tuple[str, ...] = ("10.16904", "10.24435")

# Log name, format, and date format
LOG_NAME: str = "datacite-websnap.log"
LOG_FORMAT: str = "%(asctime)s | %(levelname)s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# Threshold for switching from sequential to threading data uploads (> value)
THREADING_UPLOAD_THRESHOLD: int = 10

# Maximum number of threads that can be used to execute the given calls for data uploads
THREADING_UPLOAD_MAX_WORKERS: int = 4
