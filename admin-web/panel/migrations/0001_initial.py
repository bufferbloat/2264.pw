# Generated for the initial private webmaster deployment.
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(name="AuditEvent", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("actor_email", models.EmailField(blank=True, max_length=254)),
            ("action", models.CharField(max_length=100)),
            ("target", models.CharField(blank=True, max_length=500)),
            ("remote_ip", models.GenericIPAddressField(blank=True, null=True)),
            ("details", models.JSONField(blank=True, default=dict)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="LoginThrottle", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("key", models.CharField(max_length=64, unique=True)),
            ("failures", models.PositiveIntegerField(default=0)),
            ("window_started_at", models.DateTimeField(auto_now_add=True)),
            ("locked_until", models.DateTimeField(blank=True, null=True)),
        ]),
        migrations.CreateModel(name="TrashItem", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("kind", models.CharField(choices=[("post", "Post"), ("resource", "Resource"), ("media", "Media"), ("file", "File")], max_length=20)),
            ("label", models.CharField(max_length=500)),
            ("original_path", models.CharField(blank=True, max_length=1000)),
            ("trash_path", models.CharField(blank=True, max_length=1000)),
            ("payload", models.JSONField(blank=True, default=dict)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("expires_at", models.DateTimeField()),
            ("restored_at", models.DateTimeField(blank=True, null=True)),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="UploadSession", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("relative_path", models.CharField(max_length=1000)),
            ("total_size", models.PositiveBigIntegerField()),
            ("sha256", models.CharField(max_length=64)),
            ("chunk_size", models.PositiveIntegerField(default=16777216)),
            ("received_chunks", models.JSONField(default=list)),
            ("replace", models.BooleanField(default=False)),
            ("status", models.CharField(choices=[("uploading", "Uploading"), ("complete", "Complete"), ("cancelled", "Cancelled"), ("failed", "Failed")], default="uploading", max_length=20)),
            ("error", models.TextField(blank=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("completed_at", models.DateTimeField(blank=True, null=True)),
        ]),
        migrations.CreateModel(name="OwnerSecurity", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("encrypted_totp_secret", models.BinaryField()),
            ("enrolled_at", models.DateTimeField(auto_now_add=True)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="owner_security", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="RecoveryCode", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("code_hash", models.CharField(max_length=256)),
            ("used_at", models.DateTimeField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recovery_codes", to="panel.ownersecurity")),
        ]),
        migrations.CreateModel(name="Revision", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("kind", models.CharField(choices=[("post", "Post"), ("resources", "Resources")], max_length=20)),
            ("object_id", models.CharField(max_length=64)),
            ("label", models.CharField(blank=True, max_length=240)),
            ("snapshot", models.TextField()),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-created_at"]}),
        migrations.AddIndex(model_name="revision", index=models.Index(fields=["kind", "object_id", "-created_at"], name="panel_revi_kind_6f7b0c_idx")),
    ]

