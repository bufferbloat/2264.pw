from django.conf import settings
from django.core.management.base import BaseCommand

from panel.content import initialize_published_sources
from panel.publisher import publish_all


class Command(BaseCommand):
    help = "Create the first generated release if no active release exists."

    def handle(self, *args, **options):
        if initialize_published_sources():
            self.stdout.write("Initialized published snapshots from migrated source.")
        current = settings.GENERATED_ROOT / "current"
        if current.exists():
            self.stdout.write("Generated release already active.")
            return
        release = publish_all()
        self.stdout.write(self.style.SUCCESS(f"Activated generated release {release.name}."))
