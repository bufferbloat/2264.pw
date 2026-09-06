import shutil
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from panel.models import TrashItem, UploadSession


class Command(BaseCommand):
    help = "Permanently remove expired 30-day trash and stale upload staging data."

    def handle(self, *args, **options):
        removed = 0
        for item in TrashItem.objects.filter(restored_at__isnull=True, expires_at__lte=timezone.now()):
            if item.kind == "post" and item.trash_path:
                target = settings.CONTENT_ROOT / item.trash_path
            elif item.kind in {"file", "media"} and item.trash_path:
                root = settings.MANAGED_ROOT if item.kind == "file" else settings.MEDIA_ROOT
                target = root / "trash" / item.trash_path
            else:
                target = None
            if target and target.exists():
                shutil.rmtree(target) if target.is_dir() else target.unlink()
            if item.kind == "post" and item.payload.get("published_trash_path"):
                published_snapshot = settings.CONTENT_ROOT / item.payload["published_trash_path"]
                published_snapshot.unlink(missing_ok=True)
            item.delete()
            removed += 1
        stale = UploadSession.objects.filter(status="uploading", updated_at__lt=timezone.now() - timedelta(days=7))
        stale_count = stale.count()
        for session in stale:
            shutil.rmtree(settings.MANAGED_ROOT / "staging" / str(session.id), ignore_errors=True)
            session.status = "cancelled"
            session.error = "Expired after seven inactive days"
            session.save(update_fields=["status", "error", "updated_at"])
        self.stdout.write(f"Removed {removed} expired trash items; expired {stale_count} uploads.")
