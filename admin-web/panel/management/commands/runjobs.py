import os
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run trash cleanup and configured backup once per day."

    def handle(self, *args, **options):
        while True:
            call_command("cleanup_trash")
            password_file = os.environ.get("RESTIC_PASSWORD_FILE")
            if password_file and os.path.isfile(password_file):
                try:
                    call_command("backup_local")
                except Exception as error:
                    self.stderr.write(f"Backup failed: {error}")
            time.sleep(86400)
