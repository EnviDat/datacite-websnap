# DataCite Filters 

Repository account ID and DOI prefix are the supported filters for selecting DataCite records to export using the `bulk-export` command. 

Both filters can be used for S3 and local exports.

## Repository Account ID (`--client-id`)

!!! Note
    Applying this filter exports **all** records for the specified repository account ID.

Can be combined with `--doi-prefix` options.

Each DataCite repository has a unique account ID. To confirm the correct ID, call the [DataCite API client endpoint](https://support.datacite.org/reference/get_clients-id){target="_blank"}.

If you know a DOI but not the repository ID:

1. Go to [DataCite Commons](https://commons.datacite.org/){target="_blank"}
2. Search for the DOI, e.g. `10.16904/envidat.576`
3. Click the record → **Download Metadata** → **DataCite JSON**
4. The `"clientId"` value is the repository account ID. For `10.16904/envidat.576` it is `"ethz.wsl"`.

```bash
--client-id ethz.wsl
```

## DOI Prefix (`--doi-prefix`)

!!! Note
    Applying this filter exports **all** records for the specified DOI prefix(es).

Can be combined with `--client-id` option.

Accepts single or multiple prefix arguments:

```bash
--doi-prefix 10.16904 
```

```bash
--doi-prefix 10.16904 --doi-prefix 10.25678
```
