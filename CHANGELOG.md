# CHANGELOG

### 3.2.0 (2026-07-31)
### Feat
- support writing PSI SciCat data files to local machine
- support writing PSI SciCat data files to S3 cloud storage
### Docs
- update supported DOI prefixes
- add PSI SciCat usage instructions
### Tests
- add tests for new PSI SciCat data processing functions


## 3.1.0 (2026-06-25)
### Feat
- support writing Materials Cloud data files to local machine
- support writing Materials Cloud data files to S3 cloud storage
### Refactor
- refactor logging functions
### Docs
- update credentials section
- update supported DOI prefixes
- update documentation website references
### Tests
- add tests for new Materials Cloud data processing functions 


## 3.0.0 (2026-05-27)
### Feat
- create new `doi-export` command that exports a single DataCite DOI XML record, JSON record, and associated resource data files
- retrieve DOI metadata must pass ETH metadata validation standard
- supports exporting DOIs for the EnviDat prefix (`10.16904`)
### Refactor
- rename `export` command to `bulk-export`
- refactor logic including extracting options common to both commands
### Docs
- creat new GitLab pages for project documentation
- shorten README and linked to GitLab pages
### CI
- creat a new `pages` job in `gitlab-ci.yml`
### Tests
- add tests for new functions and classes


## 2.0.2 (2026-04-27)
### Refactor
- implement Pydantic models for DataCite API response handlers
- simplify log setup
- adjust `--page-size` validator
### Tests
- update tests to cover refactored validators

## 2.0.1 (2026-04-24)
### Refactor
- update custom log functions to improve file log handling

## 2.0.0 (2026-04-17)
### Refactor
- connect to S3 service using shared credentials file
- add CLI options `--profile-name` and `--endpoint-url`
### Docs
- document new CLI options
- update S3 usage instructions
### Tests
- update tests to cover refactored S3 client handlers

## 1.0.3 (2025-08-27)
### Docs
- update badges

## 1.0.2 (2025-06-11)
### Docs
- refine cli options table and add badge

## 1.0.1 (2025-05-27)
### Docs
- update config variables instructions
## Refactor
- handle config variables directly in config.py without env var processing

## 1.0.0 (2025-05-27)
### Docs
- add filter information to README

## 1.0.0-alpha.5 (2025-05-21)
### Refactor
- allow env vars to be loaded without virtual environment

### Docs
- update README S3 usage

## 1.0.0-alpha.4 (2025-05-21)
### Refactor 
- add timeout settings to S3 client config

## 1.0.0-alpha.3 (2025-05-21)
### Fix
- load env vars for validation

### Docs
- update README installation, usage, future development, and CLI options

## 1.0.0-alpha.2 (2025-05-02)
### Feat
- add validator that ensures that a directory path is provided if exporting records locally

### Docs
- update README local usage

### Tests
- add tests for directory path validator


## 1.0.0-alpha.1 (2025-04-30)
### First alpha release
