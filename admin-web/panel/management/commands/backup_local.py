import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create an encrypted deduplicated restic snapshot and enforce retention."

    def handle(self, *args, **options):
        password_file = os.environ.get("RESTIC_PASSWORD_FILE", "")
        if not password_file:
            raise CommandError("RESTIC_PASSWORD_FILE is not configured.")
        repository = str(settings.BACKUP_ROOT / "repository")
        environment = {**os.environ, "RESTIC_REPOSITORY": repository, "RESTIC_PASSWORD_FILE": password_file}
        if not (settings.BACKUP_ROOT / "repository" / "config").exists():
            subprocess.run(["restic", "init"], env=environment, check=True)
        databases = {
            "admin.sqlite3": Path(os.environ.get("ADMIN_DATABASE", "/srv/state/admin.sqlite3")),
            "blog-stats.sqlite3": Path(os.environ.get("BLOG_STATS_DATABASE", "/srv/blog-stats/views.sqlite3")),
        }
        missing = [str(path) for path in databases.values() if not path.is_file()]
        if missing:
            raise CommandError(f"Database backup source does not exist: {', '.join(missing)}")
        with tempfile.TemporaryDirectory(prefix="2264-database-snapshots-") as temporary:
            snapshot_root = Path(temporary)
            for name, source_path in databases.items():
                source_uri = f"{source_path.resolve().as_uri()}?mode=ro"
                with sqlite3.connect(source_uri, uri=True) as source, sqlite3.connect(snapshot_root / name) as destination:
                    source.backup(destination)
            sources = [
                settings.CONTENT_ROOT, snapshot_root / "admin.sqlite3", snapshot_root / "blog-stats.sqlite3",
                settings.GENERATED_ROOT,
                settings.MEDIA_ROOT / "public", settings.MEDIA_ROOT / "trash",
                settings.MANAGED_ROOT / "public", settings.MANAGED_ROOT / "trash",
            ]
            subprocess.run(["restic", "backup", *map(str, sources), "--tag", "2264-admin"], env=environment, check=True)
            subprocess.run(["restic", "forget", "--tag", "2264-admin", "--keep-daily", "14", "--keep-weekly", "8", "--prune"], env=environment, check=True)
        self.stdout.write(self.style.SUCCESS("Encrypted snapshot and retention completed."))
