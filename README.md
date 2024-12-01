# maria-backup-s3
Barebones backup script for MariaDB with Discord Webhook notifications.

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
- Follow `https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-environment-variables` to set up AWS credentials.
- `python -m venv venv`
- `call venv\Scripts\activate.bat`
- `pip install -r requirements.txt`
- `Run run.bat`
