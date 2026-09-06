import hashlib
import secrets
from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone

from .models import AuditEvent, LoginThrottle


MAX_FAILURES = 5
WINDOW = timedelta(minutes=15)
LOCK_TIME = timedelta(minutes=30)


def client_ip(request):
    forwarded = request.META.get("HTTP_CF_CONNECTING_IP", "")
    return forwarded or request.META.get("REMOTE_ADDR") or None


def audit(request, action, target="", **details):
    email = request.user.email if getattr(request, "user", None) and request.user.is_authenticated else getattr(request, "cf_access_email", "")
    return AuditEvent.objects.create(actor_email=email, action=action, target=target, remote_ip=client_ip(request), details=details)


def throttle_key(request, email):
    raw = f"{client_ip(request)}|{email.lower()}".encode()
    return hashlib.sha256(raw).hexdigest()


def throttle_locked(request, email):
    key = throttle_key(request, email)
    record = LoginThrottle.objects.filter(key=key).first()
    return bool(record and record.locked_until and record.locked_until > timezone.now())


def record_failure(request, email):
    key = throttle_key(request, email)
    now = timezone.now()
    with transaction.atomic():
        record, _ = LoginThrottle.objects.select_for_update().get_or_create(key=key)
        if now - record.window_started_at > WINDOW:
            record.failures = 0
            record.window_started_at = now
            record.locked_until = None
        record.failures += 1
        if record.failures >= MAX_FAILURES:
            record.locked_until = now + LOCK_TIME
        record.save()


def clear_failures(request, email):
    LoginThrottle.objects.filter(key=throttle_key(request, email)).delete()


def authenticate_owner(request, email, password, token):
    email = email.strip().lower()
    if email != settings.OWNER_EMAIL or email != getattr(request, "cf_access_email", email):
        return None, "Access identity does not match the owner."
    if throttle_locked(request, email):
        return None, "Too many attempts. Try again later."
    user = authenticate(request, username=email, password=password)
    if user is None or not user.is_active:
        record_failure(request, email)
        return None, "Invalid password or authentication code."
    try:
        owner = user.owner_security
    except Exception:
        record_failure(request, email)
        return None, "Two-factor authentication has not been enrolled."
    normalized = token.replace(" ", "").replace("-", "").upper()
    if pyotp.TOTP(owner.get_secret()).verify(normalized, valid_window=1):
        clear_failures(request, email)
        return user, None
    with transaction.atomic():
        for recovery in owner.recovery_codes.select_for_update().filter(used_at__isnull=True):
            if recovery.matches(normalized):
                recovery.used_at = timezone.now()
                recovery.save(update_fields=["used_at"])
                clear_failures(request, email)
                return user, None
    record_failure(request, email)
    return None, "Invalid password or authentication code."


def generate_recovery_codes(count=10):
    return [f"{secrets.token_hex(3)}-{secrets.token_hex(3)}".upper() for _ in range(count)]
