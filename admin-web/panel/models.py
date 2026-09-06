import base64
import hashlib
import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import models


def _fernet():
    configured = settings.TOTP_ENCRYPTION_KEY.encode("ascii") if settings.TOTP_ENCRYPTION_KEY else None
    if configured is None:
        if not settings.DEBUG:
            raise RuntimeError("TOTP_ENCRYPTION_KEY must be configured")
        configured = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(configured)


class OwnerSecurity(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="owner_security")
    encrypted_totp_secret = models.BinaryField()
    enrolled_at = models.DateTimeField(auto_now_add=True)

    def set_secret(self, secret):
        self.encrypted_totp_secret = _fernet().encrypt(secret.encode("ascii"))

    def get_secret(self):
        return _fernet().decrypt(bytes(self.encrypted_totp_secret)).decode("ascii")


class RecoveryCode(models.Model):
    owner = models.ForeignKey(OwnerSecurity, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=256)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_code(self, code):
        self.code_hash = make_password(code.replace(" ", "").replace("-", "").upper())

    def matches(self, code):
        normalized = code.replace(" ", "").replace("-", "").upper()
        return self.used_at is None and check_password(normalized, self.code_hash)


class Revision(models.Model):
    KIND_CHOICES = [("post", "Post"), ("resources", "Resources")]
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    object_id = models.CharField(max_length=64)
    label = models.CharField(max_length=240, blank=True)
    snapshot = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["kind", "object_id", "-created_at"], name="panel_revi_kind_6f7b0c_idx")]


class AuditEvent(models.Model):
    actor_email = models.EmailField(blank=True)
    action = models.CharField(max_length=100)
    target = models.CharField(max_length=500, blank=True)
    remote_ip = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class LoginThrottle(models.Model):
    key = models.CharField(max_length=64, unique=True)
    failures = models.PositiveIntegerField(default=0)
    window_started_at = models.DateTimeField(auto_now_add=True)
    locked_until = models.DateTimeField(null=True, blank=True)


class TrashItem(models.Model):
    KIND_CHOICES = [("post", "Post"), ("resource", "Resource"), ("media", "Media"), ("file", "File")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    label = models.CharField(max_length=500)
    original_path = models.CharField(max_length=1000, blank=True)
    trash_path = models.CharField(max_length=1000, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    restored_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class UploadSession(models.Model):
    STATUS_CHOICES = [
        ("uploading", "Uploading"),
        ("complete", "Complete"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relative_path = models.CharField(max_length=1000)
    total_size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    chunk_size = models.PositiveIntegerField(default=16 * 1024 * 1024)
    received_chunks = models.JSONField(default=list)
    replace = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploading")
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def total_chunks(self):
        return (self.total_size + self.chunk_size - 1) // self.chunk_size
