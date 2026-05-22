# Local Machine

Export DataCite XML metadata records to a local machine.

## Required Options

- `--destination local`
- `--directory-path` must be assigned to the path of an existing local directory


## `bulk-export` Example

```bash
datacite-websnap bulk-export --client-id ethz.wsl --destination local --directory-path "opendata/wsl"
```

- Return all DataCite metadata records for the EnviDat repository (using client-id `ethz.wsl`)
- Export the records to a local directory `opendata/wsl`


## `doi-export` Example

```bash
datacite-websnap doi-export --doi "https://www.doi.org/10.16904/envidat.518" --destination local --directory-path "opendata/wsl" 
```

- Export a single DataCite DOI XML record, JSON record, and associated resource data files
- Export the records and data files to a local directory `opendata/wsl`
