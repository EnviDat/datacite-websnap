# `bulk-export`

Bulk export DataCite XML metadata records that correspond to the records for a particular DataCite repository and/or DOI prefix.

The default behavior is to export DataCite XML records to an S3 bucket but the command also supports exporting the records to a local machine.

## Options

| Option         | Default | Description                                                                                                                                                                                                                                                                 |
|----------------|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--doi-prefix` | `None`  | <ul><li>DataCite DOI prefix used to filter results</li><li>Accepts single or multiple prefix arguments</li><li>*Example*: `--doi-prefix 10.16904 --doi-prefix 10.25678`</li></ul>                                                                                           |
| `--client-id`  | `None`  | <ul><li>DataCite repository account ID used to filter results</li><li>Referred to as the 'client-id' in the DataCite documentation</li><li>*Example*: `--client-id ethz.wsl`</li></ul>                                                                                      |
| `--early-exit` | `False` | <ul><li>If enabled, terminates the program immediately after an export error occurs</li><li>If `False`, only logs the error and continues to export other records returned by the search query</li></ul>                                                                    |
| `--page-size`  | `250`   | <ul><li>Number of records returned per page of DataCite API response using pagination</li><li>Can also be set using a DataCite API configuration variable</li></ul>                                                                                                         |

See [Common Options](common-options.md) for options shared with `doi-export`.