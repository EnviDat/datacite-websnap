# doi-export

Export a single DataCite DOI XML record, JSON record, and associated resource data files.

Only exports DataCite DOIs that pass ETH Zurich metadata standards.

The default behavior is to export DataCite records to an S3 bucket but the command also supports downloading the records to a local machine.

## Options

| Option  | Default | Description                                                                                                                                                  |
|---------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--doi` | —       | **Required.** DOI of the DataCite record to export. Only exports DOIs that pass ETH Zurich metadata standards.<br>*Example*: `--doi 10.16904/envidat.576`    |

See [Common Options](common-options.md) for options shared with `bulk-export`.