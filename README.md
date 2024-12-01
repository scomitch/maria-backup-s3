# maria-backup-s3
Barebones backup script for MariaDB with Discord Webhook notifications. Allows you to run a cron / task schedule of program to automatically backup, compress, encrypt and upload maria backup to Amazon S3.

Requirements:
- Python 3.10+
- MariaDB CLI with mariabackup
- 7-Zip CLI
- OpenSSL CLI

Commands:
- `run.bat` - Run the script with venv.

Install:
- Install Requirements.
- Configure `config.yml` and set up `BU_DB_PASSWORD` env variable.
- Set secure `BU_ENC_PASSPHRASE` env var, which will serve as encryption key.
- Configure or remove `--tables-exclude` var to your liking (using this to exclude multi-GB of logs for personal usecase).
- Follow `https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-environment-variables` to set up AWS credentials.
- `python -m venv venv`
- `call venv\Scripts\activate.bat`
- `pip install -r requirements.txt`
- `Run run.bat`

# How to restore
- Download `.xb.gz.enc` file from S3 and put in folder
- Create subfolder which will host your restored content
- Run OpenSSL command in root folder `openssl enc -d -aes-256-cbc -in <yourencbackup>.xb.gz.enc -out <unencbackup>.xb.gz -k BU_ENC_PASSPHRASE`
- Decompress `.xb.gz` file, you should now have a raw `.xb` file.
- Run `mbstream -x < <unencbackup>.xb --directory=<yoursubfolder>`
- The xb file should now be unpacked in the restored content folder.
- Prep this folder using `mariabackup --prepare --target-dir=<yoursubfolder>`
- Copyback contents of subfolder to your new MariaDB instance `mariabackup --copy-back --target-dir=<yoursubfolder>`
- Any issues, consult [MariaBackup Docs](https://mariadb.com/kb/en/mariabackup-overview/)
