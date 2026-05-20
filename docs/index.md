# datacite-websnap

CLI tool that exports DataCite records to an S3 bucket. 

Also supports exporting records to a local machine.

## Purpose

<ul class="purpose-list">
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

## Author

[Rebecca Buchholz](http://www.linkedin.com/in/rebeccabuchholz){target="_blank"} 

[EnviDat](https://www.envidat.ch){target="_blank"}  is the environmental data portal of the Swiss Federal Institute for Forest, Snow and Landscape Research WSL.

## License

[MIT License](https://git.wsl.ch/EnviDat/datacite-websnap/-/blob/main/LICENSE){target="_blank"} 