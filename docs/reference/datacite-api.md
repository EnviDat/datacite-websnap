# DataCite API

`datacite-websnap` retrieves XML metadata records from the DataCite API.

Relevant API documentation:

- [Return a list of DOIs](https://support.datacite.org/reference/get_dois)
- [Cursor-based pagination](https://support.datacite.org/docs/pagination#method-2-cursor)
- [Return a client (DataCite repository)](https://support.datacite.org/reference/get_clients-id)

## Configuration

Default values are set in `config.py`. Override them there to change API behaviour.

| Variable                        | Default                      | Description                                                                                         |
|---------------------------------|------------------------------|-----------------------------------------------------------------------------------------------------|
| `TIMEOUT`                       | `32`                         | Timeout of API requests in seconds.                                                                 |
| `DATACITE_API_URL`              | `https://api.datacite.org`   | DataCite base URL. Assigned as default to `--api-url`. Use `https://api.test.datacite.org` to test. |
| `DATACITE_API_CLIENTS_ENDPOINT` | `/clients`                   | Endpoint used to retrieve a client.                                                                 |
| `DATACITE_API_DOIS_ENDPOINT`    | `/dois`                      | Endpoint used to retrieve a list of DOIs.                                                           |
| `DATACITE_PAGE_SIZE`            | `250`                        | DOIs retrieved per page using pagination. Assigned as default to `--page-size`.                     |
