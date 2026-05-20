# `doi-export`

Export a single DataCite DOI XML record, JSON record, and associated resource data files.

The default behavior is to export DataCite records to an S3 bucket but the command also supports downloading the records to a local machine.

> **Note**: Only exports DataCite DOIs that pass ETH Zurich metadata standards.

See [S3 Bucket](../usage/s3.md) and [Local Machine](../usage/local.md) for usage examples.


## Validation

Validates the DOI against ETH Zurich metadata standards before exporting:

- Displays warnings with recommendations for improving metadata quality
- Exits with an error if validation fails

## S3 Prompts

Requests user confirmation for the following actions while using `doi-export` to export DOI records to an S3 bucket:

- Overwriting existing metadata records (XML and JSON)
- Uploading new data files
- Overwriting existing data files

## Options

| Option  | Default | Description                                                                                                                                                                                                              |
|---------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--doi` | —       | <ul><li>**Required**</li><li>DOI of the DataCite record to export</li><li>Only exports DOIs that pass ETH Zurich metadata standards</li><li>*Example*: `--doi 10.16904/envidat.576`</li></ul>                            |

See [Common Options](common-options.md) for options shared with `bulk-export`.


## Record and Data Naming

See [Metadata Record Naming](../reference/record-naming.md) to learn more about how metadata file names (or S3 keys) are assigned. 


### S3 Bucket

Objects include the formatted DOI as a prefix.

| DOI                  | Output Data Object                                       |
|----------------------|----------------------------------------------------------|
| 10.16904/envidat.518 | 10.16904_envidat.518/bacteria-metagenomics-raw-data.xlsx |
