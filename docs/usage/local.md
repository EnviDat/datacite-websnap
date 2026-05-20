# Usage: Local Machine

Export DataCite XML metadata records to a local machine.

## Required Options

- `--destination local`
- `--directory-path` — path to an existing local directory

## Example

Export all EnviDat records to a local directory:
```bash
datacite-websnap bulk-export --client-id ethz.wsl --destination local --directory-path "opendata/wsl"
```
