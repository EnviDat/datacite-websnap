# `doi-export`

Export a single DataCite DOI XML record, JSON record, and associated resource data files.

The default behavior is to export DataCite records to an S3 bucket but the command also supports downloading the records to a local machine.

!!! note
    Only exports DataCite DOIs that pass ETH Zurich metadata standards.

## Related Documentation

See [S3 Bucket](../usage/s3.md) and [Local Machine](../usage/local.md) for usage examples.


## Options

See [Common Options](common-options.md) for options shared with `bulk-export`.

| Option  | Default | Description                                                                                                                                                                                                                                                                                                                                            |
|---------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--doi` | —       | <ul><li>**Required**</li><li>DOI of the DataCite record to export</li><li>Only exports DOIs that pass ETH Zurich metadata standards</li><li>DOI can be passed in the short form (DOI only) or with the full URL form</li><li>*Example*: `--doi "10.16904/envidat.576"`</li><li>*Example*: `--doi "https://www.doi.org/10.16904/envidat.576"`</li></ul> |



## Supported DOI Prefixes

Supports exporting DOIs with the following prefixes.

| Repository                                                         | DOI Prefix  |
|--------------------------------------------------------------------|-------------|
| [EnviDat](https://envidat.ch){target="_blank"}                     | `10.16904`  |
| [Materials Cloud](https://www.materialscloud.org){target="_blank"} | `10.24435`  |
| [PSI SciCat](https://doi.psi.ch){target="_blank"}                  | `10.169071` |

[Please see special instructions for PSI SciCat Usage.](#psi-scicat-doi-special-instructions)

## Validation

Validates the DOI against ETH Zurich metadata standards before exporting:

- Displays warnings with recommendations for improving metadata quality
- Exits with an error if validation fails

## S3 Prompts

Requests user confirmation for the following actions while using `doi-export` to export DOI records to an S3 bucket:

- Overwrite existing metadata records (XML and JSON)
- Upload new data files
- Overwrite existing data files

## Record and Data Naming

See [Metadata Record Naming](../reference/record-naming.md) to learn more about how metadata file names (or S3 keys) are assigned. 


### S3 Bucket

Objects include the formatted DOI as a prefix.

| DOI                  | Output Data Object                                       |
|----------------------|----------------------------------------------------------|
| 10.16904/envidat.518 | 10.16904_envidat.518/bacteria-metagenomics-raw-data.xlsx |


## PSI SciCat DOI Special Instructions

!!! Warning
    As of July 31, 2026, the following procedure is **required** to use this tool with 
    any PSI SciCat DOI:
      
      1. Access the DOI using the [PSI SciCat website](https://doi.psi.ch){target="_blank"}
      2. Select the dataset you want to download files from and click on it
      3. Click the "Access Data" button and enter your email address
      4. Wait for an email entitled "Your public job was submitted"
      5. Wait for another email entitled "Your public job completed successfully"

    After these steps have been taken then the PSI SciCat DOIs can be used with the `doi-export` command.
    The data will be accessible for 7 days. After that time the procedure needs to be repeated. 
 