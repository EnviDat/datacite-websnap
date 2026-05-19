# Logs

Info messages and errors are always logged to the console.

To also write logs to a file, enable `--file-logs`:

```bash
datacite-websnap bulk-export --client-id ethz.wsl --bucket opendata --file-logs
```

## Configuration

Default values are set in `config.py`. Override them there to change log behaviour.

| Variable          | Default                                                                               | Description                        |
|-------------------|---------------------------------------------------------------------------------------|------------------------------------|
| `LOG_NAME`        | `"datacite-websnap.log"`                                                              | File log name                      |
| `LOG_FORMAT`      | `"%(asctime)s \| %(levelname)s \| %(module)s.%(funcName)s:%(lineno)d \| %(message)s"` | Log record format                  |
| `LOG_DATE_FORMAT` | `"%Y-%m-%d %H:%M:%S"`                                                                 | Timestamp format                   |

[Python logging.basicConfig documentation](https://docs.python.org/3/library/logging.html#logging.basicConfig)