import getpass

import pyotp
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from panel.models import OwnerSecurity, RecoveryCode
from panel.security import generate_recovery_codes


class Command(BaseCommand):
    help = "Interactively create or replace the sole owner account and TOTP enrollment."

    def handle(self, *args, **options):
        if not settings.TOTP_ENCRYPTION_KEY and not settings.DEBUG:
            raise CommandError("Set TOTP_ENCRYPTION_KEY to a Fernet key before enrolling the owner.")
        password = getpass.getpass("Owner password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise CommandError("Passwords do not match.")
        provisional = User(username=settings.OWNER_EMAIL, email=settings.OWNER_EMAIL)
        validate_password(password, provisional)
        secret = pyotp.random_base32()
        codes = generate_recovery_codes()
        with transaction.atomic():
            User.objects.filter(username=settings.OWNER_EMAIL).delete()
            user = User.objects.create_user(username=settings.OWNER_EMAIL, email=settings.OWNER_EMAIL, password=password, is_staff=False, is_superuser=False)
            security = OwnerSecurity(user=user)
            security.set_secret(secret)
            security.save()
            for code in codes:
                recovery = RecoveryCode(owner=security)
                recovery.set_code(code)
                recovery.save()
        uri = pyotp.TOTP(secret).provisioning_uri(name=settings.OWNER_EMAIL, issuer_name="2264 webmaster")
        self.stdout.write(self.style.SUCCESS("Owner created. Add this URI to the authenticator now:"))
        self.stdout.write(uri)
        self.stdout.write("\nSingle-use recovery codes (store offline; they will not be shown again):")
        for code in codes:
            self.stdout.write(code)

