import hashlib
import io
import json
import os
import sqlite3
import tempfile
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pyotp
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .content import (
    Post, load_resources, published_post_path, save_post, save_published_post,
    save_published_resources, save_resources,
)
from .models import OwnerSecurity, RecoveryCode, Revision, TrashItem
from .publisher import publish_all


class PanelTestCase(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.content = root / "content"
        self.generated = root / "generated"
        self.media = root / "media"
        self.managed = root / "managed"
        self.backups = root / "backups"
        for directory in [self.content / "posts", self.content / "published" / "posts", self.generated / "releases", self.media / "public", self.media / "staging", self.media / "trash", self.managed / "public", self.managed / "staging", self.managed / "trash", self.backups / "repository"]:
            directory.mkdir(parents=True)
        self.settings_override = override_settings(
            DEBUG=True, CF_ACCESS_REQUIRED=False, SECURE_SSL_REDIRECT=False,
            SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False,
            CONTENT_ROOT=self.content, GENERATED_ROOT=self.generated, MEDIA_ROOT=self.media,
            MANAGED_ROOT=self.managed, MIN_FREE_BYTES=0, UPLOAD_CHUNK_SIZE=4,
            MAX_UPLOAD_SIZE=1024, MAX_IMAGE_SIZE=1024 * 1024, BACKUP_ROOT=self.backups,
        )
        self.settings_override.enable()
        resources, _ = save_resources({"title": "resources", "description": "test", "categories": []})
        save_published_resources(resources)
        self.user = User.objects.create_user(username=settings.OWNER_EMAIL, email=settings.OWNER_EMAIL, password="a very long test password")

    def tearDown(self):
        self.settings_override.disable()
        self.temporary.cleanup()

    def make_post(self, published=True):
        now = timezone.now()
        post = Post(
            id="77a7d739-5223-5d49-bb54-b2f3026071c4", title="A title", slug="a-title",
            excerpt="An excerpt", published_at=now.date(), updated_at=now, published=published,
            published_slug="a-title" if published else "", body="Hello **world**.",
        )
        save_post(post)
        if published:
            save_published_post(post)
        return post

    def authenticated(self, csrf=False):
        client = Client(enforce_csrf_checks=csrf)
        client.force_login(self.user)
        return client

    def test_password_totp_and_recovery_login(self):
        secret = pyotp.random_base32()
        security = OwnerSecurity(user=self.user)
        security.set_secret(secret)
        security.save()
        recovery = RecoveryCode(owner=security)
        recovery.set_code("ABC123-DEF456")
        recovery.save()
        client = Client()
        response = client.post("/login/", {"email": self.user.email, "password": "a very long test password", "token": pyotp.TOTP(secret).now()})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        client.post("/logout/")
        response = client.post("/login/", {"email": self.user.email, "password": "a very long test password", "token": "ABC123-DEF456"})
        self.assertEqual(response.status_code, 302)
        recovery.refresh_from_db()
        self.assertIsNotNone(recovery.used_at)

    @override_settings(CF_ACCESS_REQUIRED=True, CF_ACCESS_TEAM_DOMAIN="", CF_ACCESS_AUD="")
    def test_access_fails_closed_when_not_configured(self):
        response = Client().get("/login/")
        self.assertEqual(response.status_code, 503)

    @override_settings(CF_ACCESS_REQUIRED=True, CF_ACCESS_TEAM_DOMAIN="team.cloudflareaccess.com", CF_ACCESS_AUD="audience")
    def test_access_rejects_direct_request_without_signed_token(self):
        response = Client().get("/login/")
        self.assertEqual(response.status_code, 403)

    @override_settings(CF_ACCESS_REQUIRED=True, CF_ACCESS_TEAM_DOMAIN="team.cloudflareaccess.com", CF_ACCESS_AUD="audience")
    def test_external_health_request_also_requires_access(self):
        response = Client().get("/healthz/", REMOTE_ADDR="203.0.113.10")
        self.assertEqual(response.status_code, 403)

    @override_settings(CF_ACCESS_REQUIRED=True, CF_ACCESS_TEAM_DOMAIN="team.cloudflareaccess.com", CF_ACCESS_AUD="audience")
    def test_valid_signed_access_assertion_reaches_login(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = int(timezone.now().timestamp())
        token = jwt.encode({
            "iss": "https://team.cloudflareaccess.com", "aud": ["audience"],
            "iat": now, "exp": now + 300, "email": settings.OWNER_EMAIL,
        }, private_key, algorithm="RS256", headers={"kid": "test-key"})
        with patch("panel.middleware.jwt.PyJWKClient") as jwks:
            jwks.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key=private_key.public_key())
            response = Client().get("/login/", HTTP_CF_ACCESS_JWT_ASSERTION=token)
        self.assertEqual(response.status_code, 200)

    def test_login_throttle_locks_after_five_failures(self):
        secret = pyotp.random_base32()
        security = OwnerSecurity(user=self.user)
        security.set_secret(secret)
        security.save()
        client = Client()
        form = {"email": self.user.email, "password": "wrong password", "token": "000000"}
        for _ in range(5):
            client.post("/login/", form)
        form.update(password="a very long test password", token=pyotp.TOTP(secret).now())
        response = client.post("/login/", form)
        self.assertContains(response, "Too many attempts", status_code=200)

    def test_draft_save_does_not_switch_public_release(self):
        post = self.make_post()
        publish_all()
        active_before = os.readlink(self.generated / "current")
        response = self.authenticated().post(f"/posts/{post.id}/", {
            "title": "Changed privately", "slug": post.slug, "excerpt": post.excerpt,
            "published_at": post.published_at.isoformat(), "body": "Private body", "action": "save",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(os.readlink(self.generated / "current"), active_before)
        public = (self.generated / "current" / "blog" / "a-title.html").read_text()
        self.assertNotIn("Changed privately", public)
        publish_all()
        public = (self.generated / "current" / "blog" / "a-title.html").read_text()
        self.assertNotIn("Changed privately", public)
        self.assertEqual(Revision.objects.filter(kind="post").count(), 1)

    def test_publish_switches_release_and_renders_site(self):
        post = self.make_post(False)
        publish_all()
        response = self.authenticated().post(f"/posts/{post.id}/", {
            "title": post.title, "slug": post.slug, "excerpt": post.excerpt,
            "published_at": post.published_at.isoformat(), "body": "Published **now**", "action": "publish",
        })
        self.assertEqual(response.status_code, 302)
        public = (self.generated / "current" / "blog" / "a-title.html").read_text()
        self.assertIn("<strong>now</strong>", public)
        self.assertIn("/blog/a-title", (self.generated / "current" / "sitemap.xml").read_text())

    def test_published_slug_rename_coordinates_stats_and_redirect(self):
        post = self.make_post(True)
        publish_all()
        with patch("panel.views._stats_request", return_value={}) as stats:
            response = self.authenticated().post(f"/posts/{post.id}/", {
                "title": post.title, "slug": "renamed-title", "excerpt": post.excerpt,
                "published_at": post.published_at.isoformat(), "body": post.body, "action": "publish",
            })
        self.assertEqual(response.status_code, 302)
        stats.assert_called_once_with("POST", "/internal/posts/rename", json={"old_slug": "a-title", "new_slug": "renamed-title"})
        self.assertTrue((self.generated / "current" / "blog" / "renamed-title.html").is_file())
        self.assertFalse((self.generated / "current" / "blog" / "a-title.html").exists())
        redirects = json.loads((self.content / "redirects.json").read_text())
        self.assertEqual(redirects["a-title"], "renamed-title")

    def test_failed_rename_publish_rolls_back_source_stats_and_redirect(self):
        post = self.make_post(True)
        publish_all()
        original_snapshot = published_post_path(post.id).read_text()
        with patch("panel.views._stats_request", return_value={}) as stats, patch("panel.views.prepare_release", side_effect=ValueError("render failed")):
            response = self.authenticated().post(f"/posts/{post.id}/", {
                "title": post.title, "slug": "renamed-title", "excerpt": post.excerpt,
                "published_at": post.published_at.isoformat(), "body": post.body, "action": "publish",
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn("slug: a-title", post.path.read_text())
        self.assertEqual(json.loads((self.content / "redirects.json").read_text()), {})
        self.assertEqual(published_post_path(post.id).read_text(), original_snapshot)
        self.assertEqual(stats.call_count, 2)
        self.assertTrue(stats.call_args_list[1].kwargs["json"]["rollback"])

    def test_csrf_rejects_mutation(self):
        post = self.make_post()
        response = self.authenticated(csrf=True).post(f"/posts/{post.id}/trash/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(post.path.exists())

    def test_resource_validation_rejects_non_http_url(self):
        with self.assertRaisesMessage(ValueError, "HTTP or HTTPS"):
            save_resources({"categories": [{"name": "bad", "entries": [{"title": "x", "url": "javascript:alert(1)"}]}]})

    def test_resource_category_color_is_normalized_and_validated(self):
        resources, _ = save_resources({"categories": [{"name": "accent", "color": "#AbCdEf", "entries": []}]})
        self.assertEqual(resources["categories"][0]["color"], "#abcdef")
        with self.assertRaisesMessage(ValueError, "six-digit hexadecimal"):
            save_resources({"categories": [{"name": "bad", "color": "red", "entries": []}]})

    def test_removed_resource_enters_trash_and_can_be_restored(self):
        resources, _ = save_resources({"title": "resources", "description": "test", "categories": [{
            "id": "e5f3d665-5926-5a50-a23e-269ecc117329", "name": "tech", "visible": True,
            "entries": [{"id": "55fd817d-6d9c-5216-b61e-ce96a57e7953", "title": "Guide", "url": "https://example.com", "description": "useful", "visible": True}],
        }]})
        resources["categories"][0]["entries"] = []
        client = self.authenticated()
        response = client.post("/resources/", {"resources": json.dumps(resources), "action": "save"})
        self.assertEqual(response.status_code, 302)
        item = TrashItem.objects.get(kind="resource")
        self.assertEqual(item.label, "Guide")
        response = client.post(f"/trash/{item.id}/restore/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(load_resources()["categories"][0]["entries"][0]["title"], "Guide")

    def test_resource_source_save_stays_private_across_other_publishes(self):
        publish_all()
        resources = load_resources()
        resources["description"] = "private resource draft"
        client = self.authenticated()
        response = client.post("/resources/", {"resources": json.dumps(resources), "action": "save"})
        self.assertEqual(response.status_code, 302)
        publish_all()
        public = (self.generated / "current" / "links" / "resources.html").read_text()
        self.assertNotIn("private resource draft", public)
        response = client.post("/resources/", {"resources": json.dumps(resources), "action": "publish"})
        self.assertEqual(response.status_code, 302)
        public = (self.generated / "current" / "links" / "resources.html").read_text()
        self.assertIn("private resource draft", public)

    def test_published_post_trash_and_restore_remains_private(self):
        post = self.make_post(True)
        publish_all()
        client = self.authenticated()
        response = client.post(f"/posts/{post.id}/trash/")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(post.path.exists())
        self.assertFalse(published_post_path(post.id).exists())
        self.assertFalse((self.generated / "current" / "blog" / "a-title.html").exists())
        item = TrashItem.objects.get(kind="post")
        response = client.post(f"/trash/{item.id}/restore/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(post.path.exists())
        self.assertFalse(published_post_path(post.id).exists())
        self.assertIn("published: false", post.path.read_text())

    def test_trash_item_can_be_permanently_deleted(self):
        post = self.make_post(False)
        client = self.authenticated()
        self.assertEqual(client.post(f"/posts/{post.id}/trash/").status_code, 302)
        item = TrashItem.objects.get(kind="post")
        deleted_path = self.content / item.trash_path
        self.assertTrue(deleted_path.exists())
        self.assertEqual(client.post(f"/trash/{item.id}/delete/").status_code, 302)
        self.assertFalse(deleted_path.exists())
        self.assertFalse(TrashItem.objects.filter(pk=item.id).exists())

    def test_chunk_upload_checksum_and_atomic_complete(self):
        body = b"abcdefghij"
        client = self.authenticated()
        response = client.post("/uploads/", data=json.dumps({"path": "folder/file.bin", "size": len(body), "sha256": hashlib.sha256(body).hexdigest()}), content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        upload = response.json()
        for index, chunk in enumerate([body[0:4], body[4:8], body[8:10]]):
            response = client.put(f"/uploads/{upload['id']}/chunks/{index}/", data=chunk, content_type="application/octet-stream")
            self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(client.get(f"/uploads/{upload['id']}/").json()["received"], [0, 1, 2])
        response = client.post(f"/uploads/{upload['id']}/complete/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((self.managed / "public" / "folder" / "file.bin").read_bytes(), body)

    def test_upload_rejects_traversal_and_collision_without_replace(self):
        client = self.authenticated()
        payload = {"path": "../secret", "size": 1, "sha256": hashlib.sha256(b"x").hexdigest()}
        self.assertEqual(client.post("/uploads/", data=json.dumps(payload), content_type="application/json").status_code, 400)
        payload["path"] = "/absolute/path"
        self.assertEqual(client.post("/uploads/", data=json.dumps(payload), content_type="application/json").status_code, 400)
        existing = self.managed / "public" / "exists.bin"
        existing.write_bytes(b"old")
        payload["path"] = "exists.bin"
        self.assertEqual(client.post("/uploads/", data=json.dumps(payload), content_type="application/json").status_code, 409)

    def test_checksum_failure_never_publishes_file(self):
        body = b"bad checksum"
        client = self.authenticated()
        payload = {"path": "bad.bin", "size": len(body), "sha256": hashlib.sha256(b"different").hexdigest()}
        upload = client.post("/uploads/", data=json.dumps(payload), content_type="application/json").json()
        for index in range((len(body) + 3) // 4):
            chunk = body[index * 4:(index + 1) * 4]
            self.assertEqual(client.put(f"/uploads/{upload['id']}/chunks/{index}/", data=chunk, content_type="application/octet-stream").status_code, 200)
        self.assertEqual(client.post(f"/uploads/{upload['id']}/complete/").status_code, 400)
        self.assertFalse((self.managed / "public" / "bad.bin").exists())
        self.assertEqual(client.get(f"/uploads/{upload['id']}/").json()["status"], "failed")
        self.assertFalse((self.managed / "staging" / upload["id"]).exists())

    def test_media_upload_validates_file_content(self):
        image_data = io.BytesIO()
        from PIL import Image
        Image.new("RGB", (2, 2), "red").save(image_data, format="PNG")
        client = self.authenticated()
        valid = SimpleUploadedFile("picture.bin", image_data.getvalue(), content_type="application/octet-stream")
        response = client.post("/media/upload/", {"image": valid})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue((self.media / "public" / response.json()["url"].removeprefix("/media/posts/")).is_file())
        invalid = SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")
        self.assertEqual(client.post("/media/upload/", {"image": invalid}).status_code, 400)

    def test_explicit_replace_moves_old_file_to_trash(self):
        body = b"new"
        old = self.managed / "public" / "replace.bin"
        old.write_bytes(b"old")
        client = self.authenticated()
        payload = {"path": "replace.bin", "size": len(body), "sha256": hashlib.sha256(body).hexdigest(), "replace": True}
        upload = client.post("/uploads/", data=json.dumps(payload), content_type="application/json").json()
        self.assertEqual(client.put(f"/uploads/{upload['id']}/chunks/0/", data=body, content_type="application/octet-stream").status_code, 200)
        self.assertEqual(client.post(f"/uploads/{upload['id']}/complete/").status_code, 200)
        self.assertEqual(old.read_bytes(), body)
        item = TrashItem.objects.get(kind="file")
        self.assertEqual((self.managed / "trash" / item.trash_path).read_bytes(), b"old")

    def test_disk_reserve_rejects_upload_before_staging(self):
        client = self.authenticated()
        payload = {"path": "large.bin", "size": 10, "sha256": hashlib.sha256(b"x" * 10).hexdigest()}
        with override_settings(MIN_FREE_BYTES=10**30):
            response = client.post("/uploads/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("free disk space", response.json()["error"])

    def test_expired_trash_is_permanently_cleaned(self):
        path = self.managed / "public" / "expired.bin"
        path.write_bytes(b"expired")
        client = self.authenticated()
        client.post("/files/", {"action": "trash", "path": "expired.bin"})
        item = TrashItem.objects.get(kind="file")
        trashed_path = self.managed / "trash" / item.trash_path
        item.expires_at = timezone.now() - timedelta(seconds=1)
        item.save(update_fields=["expires_at"])
        call_command("cleanup_trash")
        self.assertFalse(trashed_path.exists())
        self.assertFalse(TrashItem.objects.filter(pk=item.pk).exists())

    def test_backup_uses_consistent_sqlite_snapshot_and_retention(self):
        database = Path(self.temporary.name) / "admin.sqlite3"
        stats_database = Path(self.temporary.name) / "stats.sqlite3"
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE TABLE marker(value TEXT)")
            connection.execute("INSERT INTO marker VALUES ('safe')")
        with sqlite3.connect(stats_database) as connection:
            connection.execute("CREATE TABLE marker(value TEXT)")
            connection.execute("INSERT INTO marker VALUES ('counts')")
        (self.backups / "repository" / "config").write_text("configured")
        environment = {
            "ADMIN_DATABASE": str(database), "BLOG_STATS_DATABASE": str(stats_database),
            "RESTIC_PASSWORD_FILE": "/test/password",
        }
        with patch.dict(os.environ, environment), patch("panel.management.commands.backup_local.subprocess.run") as run:
            call_command("backup_local")
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0][0:2], ["restic", "backup"])
        self.assertTrue(any(str(path).endswith("/admin.sqlite3") for path in commands[0]))
        self.assertTrue(any(str(path).endswith("/blog-stats.sqlite3") for path in commands[0]))
        self.assertIn("--keep-daily", commands[1])
        self.assertIn("14", commands[1])
        self.assertIn("--keep-weekly", commands[1])
        self.assertIn("8", commands[1])

    def test_publish_fails_closed_on_corrupt_post_source(self):
        self.make_post(True)
        publish_all()
        active = os.readlink(self.generated / "current")
        (self.content / "published" / "posts" / "corrupt.md").write_text("not front matter")
        with self.assertRaisesMessage(ValueError, "invalid post snapshot corrupt.md"):
            publish_all()
        self.assertEqual(os.readlink(self.generated / "current"), active)
