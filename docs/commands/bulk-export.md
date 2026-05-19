# bulk-export

Bulk export DataCite XML metadata records that correspond to the records for a particular DataCite repository and/or DOI prefix.

The default behavior is to export DataCite XML records to an S3 bucket but the command also supports exporting the records to a local machine.

## Options

| Option         | Default | Description                                                                                                                                                                                                          |
|----------------|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--doi-prefix` | `None`  | DataCite DOI prefix used to filter results. Accepts single or multiple prefix arguments.<br>*Example*: `--doi-prefix 10.16904 --doi-prefix 10.25678`                                                                 |
| `--client-id`  | `None`  | DataCite repository account ID used to filter results. Referred to as the 'client-id' in the DataCite documentation.<br>*Example*: `--client-id ethz.wsl`                                                           |
| `--early-exit` | `False` | If enabled, terminates the program immediately after an export error occurs. If `False`, only logs the error and continues to export other records returned by the search query.                                      |
| `--page-size`  | `250`   | Number of records returned per page of DataCite API response using pagination. Can also be set using a DataCite API configuration variable.                                                                           |

See [Common Options](common-options.md) for options shared with `doi-export`.