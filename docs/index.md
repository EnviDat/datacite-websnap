# datacite-websnap

CLI tool that exports DataCite records to an S3 bucket. Also supports exporting records to a local machine.

## Purpose

`datacite-websnap` was developed to facilitate interoperability between the data platforms of the ETH research institutions in Switzerland.

`datacite-websnap` empowers research institutions to share their DataCite metadata records by exporting the records to publicly accessible S3 cloud storage. This tool also supports exporting a single DataCite DOI XML record, JSON record, and associated resource data files.

## Installation

```bash
pip install datacite-websnap
```

## Quick Start

```bash
# General help
datacite-websnap --help

# bulk-export help
datacite-websnap bulk-export --help

# doi-export help
datacite-websnap doi-export --help
```

## Author

[Rebecca Buchholz](http://www.linkedin.com/in/rebeccabuchholz), EnviDat Software Engineer

[EnviDat](https://www.envidat.ch) is the environmental data portal of the Swiss Federal Institute for Forest, Snow and Landscape Research WSL.

## License

[MIT License](https://github.com/EnviDat/datacite-websnap/blob/main/LICENSE)