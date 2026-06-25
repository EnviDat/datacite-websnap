# Credentials

!!! Note
    `datacite-websnap` was designed to be compatible with [Switch Cloud S3.](https://www.switch.ch/en/switch-cloud-s3){target="_blank"}
    As of June 24, 2026, Switch Cloud S3 does not support IAM-like access control.
    Therefore `datacite-websnap` uses an AWS credentials file for authentication. 

Use a shared credentials file to export records to an S3 bucket.

[Boto3 shared credentials file documentation](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html#shared-credentials-file){target="_blank"} describes the expected default location (`~/.aws/credentials`), supported configuration variables, and profiles.

!!! Warning
    Environment variables take precedence over a shared credentials file!  
    See [Boto3 credential search order](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html#configuring-credentials){target="_blank"} for details.

The CLI uses the `[default]` profile unless `--profile-name` is specified.

Example `~/.aws/credentials`:
```
[default]
aws_access_key_id=YOUR_KEY
aws_secret_access_key=YOUR_SECRET
```

With a named profile:
```
[default]
aws_access_key_id=YOUR_KEY
aws_secret_access_key=YOUR_SECRET

[dev]
aws_access_key_id=DEV_KEY
aws_secret_access_key=DEV_SECRET
```
