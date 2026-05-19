# Record Naming

Exported DataCite XML records are assigned file names (or S3 keys) derived from their DOI:

- `/` is replaced with `_`
- `.xml` is appended

## Example

| DOI | File name / S3 key |
|-----|--------------------|
| `10.16904/envidat.31` | `10.16904_envidat.31.xml` |