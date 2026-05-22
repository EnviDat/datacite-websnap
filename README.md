# datacite-websnap

<div>
    <img alt="Supported Python Versions" src="https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13|%203.14-blue">
     <a href="https://pypi.org/project/datacite-websnap" target="_blank">
        <img alt="PyPI - Version" src="https://img.shields.io/pypi/v/datacite-websnap">
    </a>
    <a href="https://github.com/EnviDat/datacite-websnap/blob/main/LICENSE" target="_blank">
      <img alt="License" src="https://img.shields.io/pypi/l/websnap?color=%232780C1">
    </a>
    <img alt="Code Style - ruff" src="https://img.shields.io/badge/style-ruff-41B5BE?style=flat">
</div>

### CLI tool that exports DataCite records to an S3 bucket. 
#### Also supports exporting records to a local machine.

---


## Purpose

<ul>
  <li>Developed to facilitate interoperability between the data platforms of the ETH research institutions in Switzerland.</li>
  <li>Empowers research institutions to share their DataCite metadata records by exporting the records to publicly accessible S3 cloud storage.</li>
  <li>Tool also supports exporting a single DataCite DOI XML record, JSON record, and associated resource data files.</li>
</ul>


## Installation

```bash
pip install datacite-websnap
```


## Terminal Documentation

### General
```bash
datacite-websnap --help
```

### Commands 
```bash
datacite-websnap bulk-export --help
```

```bash
datacite-websnap doi-export --help
```


## Documentation

See the [full documentation](https://git-pages.wsl.ch/datacite-websnap-5b86d6) for commands, usage examples, and reference.

- [Commands](https://git-pages.wsl.ch/datacite-websnap-5b86d6/commands/bulk-export/): `bulk-export`, `doi-export`, common options
- [Usage](https://git-pages.wsl.ch/datacite-websnap-5b86d6/usage/s3/): S3 bucket and local machine examples
- [Reference](https://git-pages.wsl.ch/datacite-websnap-5b86d6/reference/credentials/): credentials, filters, logs, DataCite API


## Author

<a href="http://www.linkedin.com/in/rebeccabuchholz" target="_blank">Rebecca Buchholz</a>

<a href="https://www.envidat.ch" target="_blank">EnviDat</a> is the environmental data 
portal of the Swiss Federal Institute for Forest, Snow and Landscape Research WSL. 


## Inspiration

<h3><a href="https://pypi.org/project/websnap" target="_blank">websnap</a></h3>

An EnviDat PyPI package that copies files retrieved from an API to an S3 bucket or a local machine.

## License

<a href="https://git.wsl.ch/EnviDat/datacite-websnap/-/blob/main/LICENSE" target="_blank">MIT License</a>