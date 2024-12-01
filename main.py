import mariadb
import subprocess
import datetime
import boto3
import shutil
import os
import logging
import sys
import requests
import yaml
from pathlib import Path

def load_config(config_file='config.yml'):
    """
        Load the configuration from a YAML file.

        :param config_file: The path to the configuration file.
        :return: A dictionary containing the configuration settings.
    """
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)


def send_discord_message(webhook_url, message):
    """
        Send a message to a Discord webhook.

        :param webhook_url: The URL of the Discord webhook.
        :param message: The message to send.
    """
    try:
        time = datetime.datetime.now().strftime('%H:%M:%S')
        response = requests.post(webhook_url, json={"content": time + " : " + message})
        if response.status_code == 204:
            logging.info("Discord webhook message sent successfully.")
        else:
            logging.error(f"Failed to send Discord message: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Exception while sending Discord message: {e}", exc_info=True)
        
        
def create_backup_file(backup_file, mariabackup_cmd):
    """
        Create a raw backup file using mariabackup.

        :param backup_file: The path to the backup file.
        :param mariabackup_cmd: The command to run mariabackup.
    """
    try:
        with open(backup_file, "wb") as out_file:
            # Run mariabackup and write the output to the backup file
            result = subprocess.run(mariabackup_cmd, stdout=out_file, stderr=subprocess.PIPE, check=True)
        logging.info(f"Raw backup file created: {backup_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Backup creation failed with error:\n{e.stderr.decode()}", exc_info=True)
        raise
      
        
def compress_backup_file(input_file, output_file):
    """
        Compress a backup file using 7-Zip.

        :param input_file: The path to the input file.
        :param output_file: The path to the output file.
    """
    try:
        seven_zip_cmd = [
            "7z",
            "a",
            "-tgzip",
            str(output_file),
            str(input_file)
        ]
        result = subprocess.run(seven_zip_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logging.info(f"Backup file compressed: {output_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Compression failed: {e.stderr.decode()}", exc_info=True)
        raise


def encrypt_backup_file(input_file, output_file, passphrase):
    """
        Encrypt a backup file using OpenSSL.

        :param input_file: The path to the input file.
        :param output_file: The path to the output file.
        :param passphrase: The passphrase to use for encryption.
    """
    try:
        openssl_cmd = [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-salt",
            "-k", passphrase,
            "-in", str(input_file),
            "-out", str(output_file)
        ]
        subprocess.run(openssl_cmd, check=True)
        logging.info(f"Backup file encrypted: {output_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Encryption failed: {e}", exc_info=True)
        raise


def main():
    """
        Main function to run the backup process.
    """
    try:
        config = load_config()
        server_name = config['server_name']
        discord_webhook_url = config['discord_webhook_url']

        encryption_passphrase = os.getenv('BU_ENC_PASSPHRASE')

        db_user = config['db_user']
        db_password = os.getenv('BU_DB_PASSWORD')
        db_name = config['db_name']
        db_host = config['db_host']

        logs_dir = Path('logs').resolve()
        temp_dir = Path('backup').resolve()
        logs_dir.mkdir(exist_ok=True)
        temp_dir.mkdir(exist_ok=True)

        current_datetime = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        raw_backup_file = temp_dir / f"{db_name}_backup_{current_datetime}.xb"
        compressed_backup_file = temp_dir / f"{db_name}_backup_{current_datetime}.xb.gz"
        encrypted_backup_file = temp_dir / f"{db_name}_backup_{current_datetime}.xb.gz.enc"

        log_file = logs_dir / f"mariadb_backup_{current_datetime}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logging.info("######################## NEW BACKUP BATCH ##########################")
        send_discord_message(discord_webhook_url, f"**{server_name}**: Backup process started.")
        
        logging.info("Starting compressed backup file creation...")
        send_discord_message(discord_webhook_url, f"**{server_name}**: Starting compressed backup file creation.")
        mariabackup_cmd = [
            "mariabackup",
            "--backup",
            f"--user={db_user}",
            f"--password={db_password}",
            f"--databases={db_name}",
            "--tables-exclude=logs",
            "--stream=xbstream"
        ]
        
        # Create backup
        try:
            create_backup_file(raw_backup_file, mariabackup_cmd)
            send_discord_message(discord_webhook_url, f"**{server_name}**: Compressed backup file created successfully.")
        except Exception as e:
            logging.error(f"Compressed backup creation failed: {e}", exc_info=True)
            send_discord_message(discord_webhook_url, f"**{server_name}**: Compressed backup creation failed")
            sys.exit(2)
        
        # Compress
        logging.info("Compressing the backup file...")
        send_discord_message(discord_webhook_url, f"**{server_name}**: Compressing backup file.")
        try:
            compress_backup_file(raw_backup_file, compressed_backup_file)
            send_discord_message(discord_webhook_url, f"**{server_name}**: Backup file compressed successfully.")
        except Exception as e:
            logging.error(f"Backup compression failed: {e}", exc_info=True)
            send_discord_message(discord_webhook_url, f"**{server_name}**: Backup compression failed")
            sys.exit(3)
        
        # Encrypt the raw data.
        logging.info("Encrypting the backup file...")
        send_discord_message(discord_webhook_url, f"**{server_name}**: Encrypting Backup")
        try:
            encrypt_backup_file(compressed_backup_file, encrypted_backup_file, encryption_passphrase)
            send_discord_message(discord_webhook_url, f"**{server_name}**: Backup file encrypted successfully.")
        except Exception as e:
            logging.error(f"Backup encryption failed: {e}", exc_info=True)
            send_discord_message(discord_webhook_url, f"**{server_name}**: Backup encryption failed")
            sys.exit(4)
        
        # Upload
        logging.info("Uploading encrypted backup to S3...")
        send_discord_message(discord_webhook_url, f"**{server_name}**: Uploading backup to secure cloud.")
        if not encrypted_backup_file.exists():
            logging.error(f"Encrypted backup file does not exist: {encrypted_backup_file.resolve()}")
            send_discord_message(discord_webhook_url, f"**{server_name}**: Encrypted backup file not found.")
            sys.exit(5)
        try:
            s3_client = boto3.client('s3')
            s3_bucket_name = config['s3_bucket_name']
            s3_client.upload_file(str(encrypted_backup_file.resolve()), s3_bucket_name, encrypted_backup_file.name)
            logging.info(f"Encrypted backup {encrypted_backup_file.name} uploaded to S3 bucket.")
            send_discord_message(discord_webhook_url, f"**{server_name}**: Encrypted backup uploaded to S3 successfully.")
        except Exception as e:
            logging.error(f"S3 upload failed: {e}", exc_info=True)
            send_discord_message(discord_webhook_url, f"**{server_name}**: S3 upload failed")
            sys.exit(6)
            
        logging.info("Cleaning up local backup files...")
        send_discord_message(discord_webhook_url, f"**{server_name}**: Cleaning up...")
        try:
            if raw_backup_file.exists():
                raw_backup_file.unlink()
            if compressed_backup_file.exists():
                compressed_backup_file.unlink()
            if encrypted_backup_file.exists():
                encrypted_backup_file.unlink()
            logging.info("Local backup files cleaned up.")
            send_discord_message(discord_webhook_url, f"**{server_name}**: Cleanup finished.")
        except Exception as e:
            logging.error(f"Cleanup failed: {e}", exc_info=True)
        
        send_discord_message(discord_webhook_url, f"**{server_name}**: Backup successfully completed.")
        
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        send_discord_message(discord_webhook_url, f"**{server_name}**: An unexpected error occurred")
        sys.exit(99)


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        logging.error(f"Exited with code: {e.code}")
        sys.exit(e.code)
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(100)
