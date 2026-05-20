# Metadata Record Naming

Exported DataCite metadata records are assigned file names (or S3 keys) derived from their DOI:

- `/` and `:` are replaced with `_`
- `.xml` or `.json` is appended

| DOI                    | Metadata File Name / S3 Key |
|------------------------|-----------------------------|
| `10.16904/envidat.518` | `10.16904_envidat.518.xml`  |
| `10.16904/envidat.518` | `10.16904_envidat.518.json` |
