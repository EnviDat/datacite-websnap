# datacite-websnap

<div>
    <img alt="Tested Python Versions" src="https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue"> 
    <img alt="License" src="https://img.shields.io/pypi/l/websnap?color=%232780C1">
    <a href="https://gitlabext.wsl.ch/EnviDat/datacite-websnap/-/blob/main/LICENSE" target="_blank">
      <img alt="License" src="https://img.shields.io/pypi/l/websnap?color=%232780C1">
    </a>
    <img alt="Code Style - ruff" src="https://img.shields.io/badge/style-ruff-41B5BE?style=flat">
    <img alt="Coverage" src="https://gitlabext.wsl.ch/EnviDat/datacite-websnap/badges/main/coverage.svg">
</div>

### CLI tool that bulk exports DataCite metadata records for a specific repository to an S3 bucket. 
#### Also supports exporting repository records to a local machine.

---


## Purpose

`datacite-websnap` was developed to facilitate interoperability between the data platforms of the ETH research institutions in Switzerland. 

`datacite-websnap` empowers research institutions to share their DataCite metadata records by exporting the records to publicly accessible S3 cloud storage.  



## Installation

<details>
  <summary>Click to unfold</summary>

_To run the test suite the repository must be cloned rather than installed as a package._ 

### Package

Install the package:

```bash
pip install datacite-websnap --index-url https://gitlabext.wsl.ch/api/v4/projects/552/packages/pypi/simple
```

### Clone Repository

Install the repository including the development dependencies used for the test suite:

1. Clone the repository
    ```bash
    git clone https://gitlabext.wsl.ch/EnviDat/datacite-websnap.git
    ```

2. Navigate to the `datacite-websnap` directory
    ```bash
    cd datacite-websnap 
    ```

3. Install PDM if needed
    ```bash
    pip install pdm 
    ```

4. Install all dependencies including dev dependencies
    ```bash
    pdm install --dev
    ```

</details>


## Terminal Documentation

To access CLI documentation:
   ```bash
    datacite-websnap --help
   ```

To access more detailed documentation for the `export` command:
   ```bash
      datacite-websnap export --help
   ```

## CLI Options

<details>
  <summary>Click to unfold</summary>

### Command: `export`

Bulk export DataCite XML metadata records that correspond to the records for a particular DataCite repository and/or DOI prefix.

The default behavior is to export DataCite XML records to an S3 bucket but command also supports exporting the records to a local machine.

| Option             | Default                    | Description                                                                                                                                                                                                                                                                                                                                           |
|--------------------|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--doi-prefix`     | `None`                     | <ul><li>DataCite DOI prefix used to filter results</li><li>Accepts single or multiple prefix arguments</li><li>*Example*: `--doi-prefix 10.16904 --doi-prefix 10.25678`</li></ul>                                                                                                                                                                     |
| `--client-id`      | `None`                     | <ul><li>DataCite repository account ID used to filter results</li><li>Referred to as the "client-id" in the DataCite API documentation</li><li>*Example*: `--client-id ethz.wsl`</li></ul>                                                                                                                                                            |
| `--destination`    | `S3`                       | <ul><li>Export destination for the DataCite XML records</li><li>`S3` (default) for an S3 bucket</li><li>`local` for local file system</li></ul>                                                                                                                                                                                                       |
| `--bucket`         | `None`                     | <ul><li>Name of S3 bucket that DataCite XML records (as S3 objects) will be written in</li><li>*Example*: `--bucket opendataswiss`</li><ul>                                                                                                                                                                                                           |
| `--key-prefix`     | `None`                     | <ul><li>Optional key prefix for objects in S3 bucket</li><li>If omitted then objects are written in S3 bucket without a prefix</li><li>*Example*: `--key-prefix wsl`</li></ul>                                                                                                                                                                        |
| `--directory-path` | `None`                     | <ul><li>Only used if exporting to `local` destination<li>Path of the local directory that DataCite XML records will be written in </li></ul>                                                                                                                                                                                                          |
| `--file-logs`      | `False`                    | <ul><li>Enables logging info messages and errors to a file log</li></ul>                                                                                                                                                                                                                                                                              |
| `--log-level`      | `INFO`                     | <ul><li>Level to use for logging if using `--file-logs` option</li><li>Default value is `INFO`</li><li>Valid logging levels are `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`</li><li><a href="https://docs.python.org/3/library/logging.html#logging-levels" target="_blank">Click here to learn more about Python logging levels</a></li></ul> |
| `--early-exit`     | `False`                    | <ul><li>If enabled then terminates program immediately after export error occurs</li><li>Default value is `False` (not enabled)</li><li>If `False` then only logs export error and continues to try to export other DataCite XML records returned by search query</li></ul>                                                                           |
| `--api-url`        | `https://api.datacite.org` | <ul><li>DataCite API base URL used for queries</li></ul>                                                                                                                                                                                                                                                                                              |
| `--page-size`      | `250`                      | <ul><li>Number of records returned per page of DataCite API response using pagination</li></ul>                                                                                                                                                                                                                                                       |

</details>


## Usage: S3 Bucket

<details>
  <summary>
  Click to unfold
  </summary>

Utilizes the AWS SDK for Python (Boto3) to export DataCite XML metadata records for a specific repository and/or DOI prefix as objects in an S3 bucket. 


### Environment Variables 

The environment variables listed below are **required** to export records to an S3 bucket.

| Environment Variable    | Description                              |
|-------------------------|------------------------------------------|
| `ENDPOINT_URL`          | URL to use for the constructed S3 client |
| `AWS_ACCESS_KEY_ID`     | AWS access key ID                        |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key                    |


Supports setting environment variables in a `.env` file.

Example `.env` file:

```
ENDPOINT_URL=https://dreamycloud.com
AWS_ACCESS_KEY_ID=1234567abcdefg
AWS_SECRET_ACCESS_KEY=hijklmn1234567
```

### Examples

#### Basic Usage

- Return all DataCite records for the EnviDat repository (using client-id `ethz.wsl`)
- Write XML records to a bucket called "opendataswiss" 

```bash
datacite-websnap export --client-id ethz.wsl --bucket opendataswiss
```

#### Advanced Usage

- Return all DataCite records for the EnviDat repository (using client-id `ethz.wsl`)
- Write XML records to a bucket called "opendataswiss" 
- Use key prefix `wsl`
- Enable logging to a file

```bash
datacite-websnap export --client-id ethz.wsl --bucket opendataswiss --key-prefix wsl --file-logs
```

</details>



## Usage: Local Machine

<details>
  <summary>
  Click to unfold
  </summary>

Export DataCite XML metadata records for a specific repository and/or DOI prefix to a local machine. 

To write the records locally the `--destination` option **must** be assigned to `local`. 

### Example

- Return all DataCite records for the EnviDat repository (using client-id `ethz.wsl`)
- Write XML records locally
- Write XML records to a directory called "samples/test"

```bash
datacite-websnap export --client-id ethz.wsl --destination local --directory-path "samples/test"
```

</details>


## Record Name Formatting

<details>
  <summary>
  Click to unfold
  </summary>

Exported DataCite XML records are assigned file names (or S3 keys) using the DOI that corresponds to the record.

- The "/" slash character that divides the DOI prefix and suffix are replaced with a "_" underscore character
- ".xml" is appended to the DOI as a file extension 

### Example

Record DOI: `10.16904/envidat.31`

File name (or S3 key) for exported record: `10.16904_envidat.31.xml`

</details>


## Logs

<details>
  <summary>
  Click to unfold
  </summary>

Info messages and errors are logged to the console.

Optionally log messages errors can be written to a file log called by default `"datacite-websnap.log"`.

To enable file logs the following option **must** be enabled: `--file-logs`

### Example   
```bash
datacite-websnap export --client-id ethz.wsl --bucket opendataswiss --file-logs            
```

### Environment Variables: Logs

Default environment variables are assigned in `config.py` for logging configuration.

To override the default environment variables related to logging the variables in the table below can be set in a `.env` file. 

`LOG_NAME` is the name of the file log (used if the `--file-logs` option is enabled).

<a href="https://docs.python.org/3/library/logging.html#logging.basicConfig" target="_blank">Python logging basic configuration documentation.</a>

| Environment Variable | Default                                                                               |
|----------------------|---------------------------------------------------------------------------------------|
| `LOG_NAME`           | `"datacite-websnap.log"`                                                              |
| `LOG_FORMAT`         | `"%(asctime)s \| %(levelname)s \| %(module)s.%(funcName)s:%(lineno)d \| %(message)s"` |
| `LOG_DATE_FORMAT`    | `"%Y-%m-%d %H:%M:%S"`                                                                 |


</details>


## DataCite API

<details>
  <summary>
  Click to unfold
  </summary>

`datacite-websnap` retrieves XML metadata records from the DataCite API.

Documentation for the DataCite API endpoints and pagination used in `datacite-websnap`:
- <a href="https://support.datacite.org/reference/get_dois" target="_blank">Return a list of DOIs</a>
- <a href="https://support.datacite.org/docs/pagination#method-2-cursor" target="_blank">Cursor-based pagination</a>
- <a href="https://support.datacite.org/reference/get_clients-id" target="_blank">Return a client (DataCite repository)</a>

### Environment Variables: DataCite API 

Default environment variables are assigned in `config.py` for DataCite API base URL, endpoints, page size and timeout.

To override the default environment variables related to DataCite the variables in the table below can be set in a `.env` file. 

| Environment Variable            | Default                    | Description                                         |
|---------------------------------|----------------------------|-----------------------------------------------------|
| `TIMEOUT`                       | `32`                       | Timeout of API requests in seconds.                 |
| `DATACITE_API_URL`              | `https://api.datacite.org` | DataCite base URL used for API requests.            |
| `DATACITE_API_CLIENTS_ENDPOINT` | `/clients`                 | Endpoint used to retrieve client.                   |
| `DATACITE_API_DOIS_ENDPOINT`    | `/dois`                    | Endpoint used to retrieve list of DOIs.             |
| `DATACITE_PAGE_SIZE`            | `250`                      | Number of DOIs retrieved per page using pagination. |


</details>


## Tests

<details>
  <summary>
  Click to unfold
  </summary>


Both `pytest` and `tox` can be used to run the test suite for `datacite-websnap`.

To run pytest and print coverage to terminal:
```bash
pdm run pytest --cov=datacite_websnap --cov-report=term
```

To test `datacite-websnap` using the Python versions configured in `tox.ini` (see the `envlist` setting):
```bash
pdm run tox
```

</details>


## Future Development

- Review `--key-prefix` option, possibly default to the prefix of the DOI
- GitLab CI/CD pipeline:
  - possibly log in to Docker Hub
  - fix manual tox tests


## Project Status

May 2, 2025: `datacite-websnap` is in alpha testing 


## Author

<a href="http://www.linkedin.com/in/rebeccabuchholz" target="_blank">Rebecca Buchholz,</a> 
EnviDat Software Engineer

<a href="https://www.envidat.ch" target="_blank">EnviDat</a> is the environmental data 
portal of the Swiss Federal Institute for Forest, Snow and Landscape Research WSL. 


## Inspiration

<h3><a href="https://pypi.org/project/websnap" target="_blank">websnap</a></h3>

An EnviDat PyPI package that copies files retrieved from an API to an S3 bucket or a local machine.

## License

<a href="https://gitlabext.wsl.ch/EnviDat/datacite-websnap/-/blob/main/LICENSE" target="_blank">MIT License</a>