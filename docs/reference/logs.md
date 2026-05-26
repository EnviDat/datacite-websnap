# Logs

Info messages and errors are always logged to the console.

To also write logs to a file, enable `--file-logs`:

```bash
datacite-websnap bulk-export --client-id ethz.wsl --bucket opendata --file-logs
```

## Configuration

[Python logging basic configuration documentation](https://docs.python.org/3/library/logging.html#logging.basicConfig){target="_blank"}

Default values are set in `config.py`. Override them there if running from source to change log behaviour.

| Variable          | Default                                         | Description       |
|-------------------|-------------------------------------------------|-------------------|
| `LOG_NAME`        | `"datacite-websnap.log"`                        | File log name     |
| `LOG_FORMAT`      | `"%(asctime)s \| %(levelname)s \| %(message)s"` | Log record format |
| `LOG_DATE_FORMAT` | `"%Y-%m-%d %H:%M:%S"`                           | Timestamp format  |

