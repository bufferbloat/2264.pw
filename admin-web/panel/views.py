import json
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import requests
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .content import (
    Post, atomic_write, get_post, list_posts, load_resources, parse_post,
    published_post_path, published_resources_path, register_redirect,
    save_post, save_published_post, save_published_resources, save_resources,
    validate_resources,
)
from .models import AuditEvent, Revision, TrashItem, UploadSession
from .publisher import prepare_release, activate_release, publish_lock, render_preview
from .security import audit, authenticate_owner
from .storage import cancel_upload, complete_upload, create_upload, public_path, received_chunk_indices, safe_relative, store_chunk, trash_path


def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("Request body must be valid JSON.") from error


def _post_or_404(post_id):
    try:
        return get_post(post_id)
    except (FileNotFoundError, ValueError, OSError):
        raise Http404


def _stats_request(method, path, **kwargs):
    if not settings.STATS_INTERNAL_TOKEN:
        raise RuntimeError("STATS_INTERNAL_TOKEN is not configured")
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {settings.STATS_INTERNAL_TOKEN}"
    response = requests.request(method, f"{settings.STATS_INTERNAL_URL}{path}", headers=headers, timeout=8, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}


def health(request):
    return JsonResponse({"status": "ok"})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        user, error = authenticate_owner(request, email, request.POST.get("password", ""), request.POST.get("token", ""))
        if user:
            login(request, user)
            request.session.cycle_key()
            audit(request, "login.success")
            destination = request.GET.get("next", "")
            if not url_has_allowed_host_and_scheme(destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                destination = "dashboard"
            return redirect(destination)
        audit(request, "login.failure", target=email)
    return render(request, "panel/login.html", {"owner_email": settings.OWNER_EMAIL, "error": error})


@login_required
@require_POST
def logout_view(request):
    audit(request, "logout")
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    posts = list_posts()
    stats = {}
    try:
        stats = _stats_request("GET", "/internal/posts/stats").get("posts", {})
    except Exception:
        messages.warning(request, "Post statistics are currently unavailable.")
    uploads = UploadSession.objects.filter(status="uploading").count()
    return render(request, "panel/dashboard.html", {
        "posts": posts, "published_count": sum(post.published for post in posts),
        "stats": stats, "upload_count": uploads, "trash_count": TrashItem.objects.filter(restored_at__isnull=True).count(),
        "audit_events": AuditEvent.objects.all()[:8],
    })


@login_required
def post_list(request):
    posts = list_posts()
    stats = {}
    try:
        stats = _stats_request("GET", "/internal/posts/stats").get("posts", {})
    except Exception:
        pass
    return render(request, "panel/posts.html", {"posts": posts, "stats": stats})


@login_required
@require_POST
def post_create(request):
    now = timezone.now()
    post = Post(
        id=str(uuid.uuid4()), title="Untitled post", slug=f"untitled-{now:%Y%m%d-%H%M%S}", excerpt="Add an excerpt.",
        published_at=now.date(), updated_at=now, body="Start writing here.\n",
    )
    raw = save_post(post)
    Revision.objects.create(kind="post", object_id=post.id, label=post.title, snapshot=raw, created_by=request.user)
    audit(request, "post.create", post.id, slug=post.slug)
    return redirect("post_edit", post_id=post.id)


def _post_from_form(request, existing):
    body = request.POST.get("body", "")
    media = sorted(set(re.findall(r"(?:https://2264\.eu)?(/(?:media/posts|assets/img)/[^\s)\"']+)", body)))
    return Post(
        id=existing.id,
        title=request.POST.get("title", ""),
        slug=request.POST.get("slug", ""),
        excerpt=request.POST.get("excerpt", ""),
        published_at=request.POST.get("published_at", ""),
        updated_at=timezone.now(),
        published=existing.published,
        published_slug=existing.published_slug,
        media=media,
        body=body,
    )


@login_required
@require_http_methods(["GET", "POST"])
def post_edit(request, post_id):
    post = _post_or_404(post_id)
    if request.method == "POST":
        action = request.POST.get("action", "save")
        try:
            edited = _post_from_form(request, post)
            if action in {"publish", "unpublish"}:
                original_raw = post.path.read_text(encoding="utf-8")
                redirects_path = settings.CONTENT_ROOT / "redirects.json"
                original_redirects = redirects_path.read_text(encoding="utf-8") if redirects_path.exists() else "{}\n"
                snapshot_path = published_post_path(edited.id)
                snapshot_existed = snapshot_path.exists()
                original_snapshot = snapshot_path.read_text(encoding="utf-8") if snapshot_existed else ""
                old_slug = edited.published_slug
                edited.published = action == "publish"
                stats_migrated = False
                with publish_lock():
                    try:
                        # Validate uniqueness and reserved historical slugs before
                        # statistics are merged, because merging is intentionally lossy
                        # when both slugs contain the same visitor ID.
                        raw = save_post(edited)
                        if edited.published and old_slug and old_slug != edited.slug:
                            _stats_request("POST", "/internal/posts/rename", json={"old_slug": old_slug, "new_slug": edited.slug})
                            stats_migrated = True
                            register_redirect(old_slug, edited.slug)
                        if edited.published:
                            edited.published_slug = edited.slug
                        raw = save_post(edited)
                        if edited.published:
                            save_published_post(edited)
                        else:
                            snapshot_path.unlink(missing_ok=True)
                        prepared = prepare_release()
                        activate_release(prepared)
                    except Exception:
                        atomic_write(post.path, original_raw)
                        atomic_write(redirects_path, original_redirects)
                        if snapshot_existed:
                            atomic_write(snapshot_path, original_snapshot)
                        else:
                            snapshot_path.unlink(missing_ok=True)
                        if stats_migrated:
                            _stats_request("POST", "/internal/posts/rename", json={"old_slug": edited.slug, "new_slug": old_slug, "rollback": True})
                        raise
                Revision.objects.create(kind="post", object_id=edited.id, label=edited.title, snapshot=raw, created_by=request.user)
                audit(request, f"post.{action}", edited.id, slug=edited.slug, former_slug=old_slug)
                messages.success(request, f"Post {action}ed and public output regenerated.")
            else:
                raw = save_post(edited)
                Revision.objects.create(kind="post", object_id=edited.id, label=edited.title, snapshot=raw, created_by=request.user)
                audit(request, "post.save", edited.id, slug=edited.slug)
                messages.success(request, "Draft source saved. Public files were not changed.")
            return redirect("post_edit", post_id=edited.id)
        except Exception as error:
            post = locals().get("edited", post)
            messages.error(request, str(error))
    revisions = Revision.objects.filter(kind="post", object_id=post.id)[:30]
    media_items = []
    media_root = settings.MEDIA_ROOT / "public"
    if media_root.exists():
        paths = (path for path in media_root.rglob("*") if path.is_file() and not path.name.startswith("."))
        for path in sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True):
            relative = str(path.relative_to(media_root))
            media_items.append({"name": path.name, "url": f"/media/posts/{relative}"})
    return render(request, "panel/post_edit.html", {"post": post, "revisions": revisions, "media_items": media_items[:60]})


@login_required
@require_POST
@xframe_options_sameorigin
def post_preview(request, post_id):
    existing = _post_or_404(post_id)
    try:
        post = _post_from_form(request, existing).validate()
        return HttpResponse(render_preview(post))
    except Exception as error:
        return HttpResponse(f"Preview error: {error}", status=400, content_type="text/plain")


@login_required
@require_POST
def post_restore_revision(request, post_id, revision_id):
    current = _post_or_404(post_id)
    revision = get_object_or_404(Revision, pk=revision_id, kind="post", object_id=str(post_id))
    restored = parse_post(revision.snapshot, str(post_id))
    # Restoring source is deliberately private. Preserve the actual live-state
    # markers until the owner explicitly chooses Publish or Unpublish.
    restored.published = current.published
    restored.published_slug = current.published_slug
    restored.updated_at = timezone.now()
    raw = save_post(restored)
    Revision.objects.create(kind="post", object_id=restored.id, label=f"Restored: {restored.title}", snapshot=raw, created_by=request.user)
    audit(request, "post.revision_restore", restored.id, revision=revision.id)
    messages.success(request, "Revision restored as source only; publish to update the public site.")
    return redirect("post_edit", post_id=post_id)


@login_required
@require_POST
def post_trash(request, post_id):
    post = _post_or_404(post_id)
    destination = settings.CONTENT_ROOT / "trash" / "posts" / uuid.uuid4().hex / post.path.name
    snapshot = published_post_path(post.id)
    snapshot_destination = destination.with_suffix(".published.md")
    item = None
    with publish_lock():
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(post.path, destination)
            snapshot_moved = snapshot.exists()
            if snapshot_moved:
                os.replace(snapshot, snapshot_destination)
            payload = {"was_published": snapshot_moved}
            if snapshot_moved:
                payload["published_trash_path"] = str(snapshot_destination.relative_to(settings.CONTENT_ROOT))
            item = TrashItem.objects.create(
                kind="post", label=post.title, original_path=str(post.path.relative_to(settings.CONTENT_ROOT)),
                trash_path=str(destination.relative_to(settings.CONTENT_ROOT)), payload=payload,
                expires_at=timezone.now() + timedelta(days=settings.TRASH_DAYS),
            )
            if snapshot_moved:
                prepared = prepare_release()
                activate_release(prepared)
        except Exception as error:
            post.path.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                os.replace(destination, post.path)
            if snapshot_destination.exists():
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                os.replace(snapshot_destination, snapshot)
            if item:
                item.delete()
            messages.error(request, f"Post was not trashed because public regeneration failed: {error}")
            return redirect("post_edit", post_id=post.id)
    audit(request, "post.trash", post.id, trash_id=str(item.id))
    messages.success(request, "Post moved to 30-day trash.")
    return redirect("post_list")


def _record_resource_deletions(old, new, user):
    old_categories = {category["id"]: category for category in old["categories"]}
    new_categories = {category["id"]: category for category in new["categories"]}
    now = timezone.now()
    for category_id, category in old_categories.items():
        if category_id not in new_categories:
            TrashItem.objects.create(kind="resource", label=category["name"], payload={"type": "category", "value": category}, expires_at=now + timedelta(days=settings.TRASH_DAYS))
            continue
        old_entries = {entry["id"]: entry for entry in category["entries"]}
        new_ids = {entry["id"] for entry in new_categories[category_id]["entries"]}
        for entry_id, entry in old_entries.items():
            if entry_id not in new_ids:
                TrashItem.objects.create(kind="resource", label=entry["title"], payload={"type": "entry", "category_id": category_id, "value": entry}, expires_at=now + timedelta(days=settings.TRASH_DAYS))


@login_required
@require_http_methods(["GET", "POST"])
def resources_edit(request):
    resources = load_resources()
    if request.method == "POST":
        try:
            incoming = json.loads(request.POST.get("resources", "{}"))
            previous_resources = resources
            normalized, raw = save_resources(incoming)
            resources = normalized
            _record_resource_deletions(previous_resources, normalized, request.user)
            Revision.objects.create(kind="resources", object_id="resources", label="Resources", snapshot=raw, created_by=request.user)
            if request.POST.get("action") == "publish":
                snapshot_path = published_resources_path()
                snapshot_existed = snapshot_path.exists()
                original_snapshot = snapshot_path.read_text(encoding="utf-8") if snapshot_existed else ""
                with publish_lock():
                    try:
                        save_published_resources(normalized)
                        prepared = prepare_release()
                        activate_release(prepared)
                    except Exception:
                        if snapshot_existed:
                            atomic_write(snapshot_path, original_snapshot)
                        else:
                            snapshot_path.unlink(missing_ok=True)
                        raise
                audit(request, "resources.publish")
                messages.success(request, "Resources saved and published.")
            else:
                audit(request, "resources.save")
                messages.success(request, "Resources saved as source only.")
            return redirect("resources_edit")
        except Exception as error:
            messages.error(request, str(error))
    revisions = Revision.objects.filter(kind="resources", object_id="resources")[:20]
    return render(request, "panel/resources.html", {"resources": resources, "revisions": revisions})


@login_required
@require_POST
def resources_restore_revision(request, revision_id):
    revision = get_object_or_404(Revision, pk=revision_id, kind="resources", object_id="resources")
    normalized, raw = save_resources(json.loads(revision.snapshot))
    Revision.objects.create(kind="resources", object_id="resources", label="Restored resources", snapshot=raw, created_by=request.user)
    audit(request, "resources.revision_restore", revision.id)
    messages.success(request, "Resource revision restored as source only.")
    return redirect("resources_edit")


@login_required
@require_POST
@xframe_options_sameorigin
def resources_preview(request):
    try:
        resources = validate_resources(json.loads(request.POST.get("resources", "{}")))
        page = render_to_string("publish/resources.html", {"resources": resources, "origin": settings.PUBLIC_SITE_ORIGIN})
        return HttpResponse(page)
    except Exception as error:
        return HttpResponse(f"Preview error: {error}", status=400, content_type="text/plain")


def _directory_entries(relative):
    directory = public_path(relative, allow_empty=True)
    if not directory.exists() or not directory.is_dir():
        raise Http404
    entries = []
    for path in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        if path.name.startswith(".") or path.is_symlink():
            continue
        stat = path.stat()
        entries.append({"name": path.name, "relative": str(path.relative_to(settings.MANAGED_ROOT / "public")), "is_dir": path.is_dir(), "size": stat.st_size, "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone())})
    return entries


@login_required
@require_http_methods(["GET", "POST"])
def files(request):
    relative = request.GET.get("path", "")
    try:
        normalized_relative = safe_relative(relative, allow_empty=True)
        relative = str(normalized_relative) if normalized_relative.parts else ""
        if request.method == "POST":
            action = request.POST.get("action")
            target = public_path(request.POST.get("path", ""))
            if action == "mkdir":
                target.mkdir(parents=False, exist_ok=False)
            elif action == "trash":
                trash_path(target)
            elif action in {"rename", "move"}:
                destination = public_path(request.POST.get("destination", ""))
                if destination.exists():
                    raise FileExistsError("Destination already exists.")
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, destination)
            else:
                raise ValueError("Unknown file action.")
            audit(request, f"file.{action}", str(target.relative_to(settings.MANAGED_ROOT / "public")))
            messages.success(request, "File operation completed.")
            return redirect(f"/files/?path={relative}")
        entries = _directory_entries(relative)
    except Exception as error:
        if isinstance(error, Http404):
            raise
        messages.error(request, str(error))
        relative = ""
        entries = []
    crumbs = []
    partial = []
    for part in safe_relative(relative, allow_empty=True).parts:
        partial.append(part)
        crumbs.append((part, "/".join(partial)))
    return render(request, "panel/files.html", {"path": relative, "entries": entries, "crumbs": crumbs, "chunk_size": settings.UPLOAD_CHUNK_SIZE})


@login_required
@require_GET
def file_download(request):
    try:
        path = public_path(request.GET.get("path", ""))
    except ValueError:
        raise Http404
    if not path.is_file():
        raise Http404
    audit(request, "file.download", str(path.relative_to(settings.MANAGED_ROOT / "public")))
    return FileResponse(open(path, "rb"), as_attachment=True, filename=path.name)


@login_required
@require_http_methods(["POST"])
def upload_create(request):
    try:
        data = _json_body(request)
        session = create_upload(data.get("path"), data.get("size"), data.get("sha256"), data.get("replace", False))
        audit(request, "upload.create", session.relative_path, size=session.total_size)
        return JsonResponse({"id": str(session.id), "chunkSize": session.chunk_size, "totalChunks": session.total_chunks}, status=201)
    except FileExistsError as error:
        return JsonResponse({"error": str(error)}, status=409)
    except Exception as error:
        return JsonResponse({"error": str(error)}, status=400)


@login_required
@require_http_methods(["GET"])
def upload_status(request, upload_id):
    session = get_object_or_404(UploadSession, pk=upload_id)
    received = received_chunk_indices(session) if session.status == "uploading" else session.received_chunks
    return JsonResponse({
        "id": str(session.id), "status": session.status, "received": received,
        "totalChunks": session.total_chunks, "chunkSize": session.chunk_size,
        "path": session.relative_path, "size": session.total_size,
        "sha256": session.sha256, "error": session.error,
    })


@login_required
@require_http_methods(["PUT"])
def upload_chunk(request, upload_id, index):
    session = get_object_or_404(UploadSession, pk=upload_id)
    try:
        store_chunk(session, index, request.body)
        return JsonResponse({"received": index})
    except Exception as error:
        return JsonResponse({"error": str(error)}, status=400)


@login_required
@require_POST
def upload_complete(request, upload_id):
    session = get_object_or_404(UploadSession, pk=upload_id)
    try:
        destination = complete_upload(session)
        audit(request, "upload.complete", session.relative_path, sha256=session.sha256)
        return JsonResponse({"path": str(destination.relative_to(settings.MANAGED_ROOT / "public")), "sha256": session.sha256})
    except FileExistsError as error:
        return JsonResponse({"error": str(error)}, status=409)
    except Exception as error:
        return JsonResponse({"error": str(error)}, status=400)


@login_required
@require_POST
def upload_cancel(request, upload_id):
    session = get_object_or_404(UploadSession, pk=upload_id)
    cancel_upload(session)
    audit(request, "upload.cancel", session.relative_path)
    return JsonResponse({"status": "cancelled"})


@login_required
@require_POST
def media_upload(request):
    upload = request.FILES.get("image")
    if not upload or upload.size > settings.MAX_IMAGE_SIZE:
        return JsonResponse({"error": "Image is required and must not exceed 25 MiB."}, status=400)
    extension_by_format = {"PNG": ".png", "JPEG": ".jpg", "GIF": ".gif", "WEBP": ".webp"}
    staging = settings.MEDIA_ROOT / "staging" / f"{uuid.uuid4().hex}.upload"
    staging.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(staging, "xb") as output:
            for chunk in upload.chunks():
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        with Image.open(staging) as image:
            extension = extension_by_format.get(image.format)
            if image.width * image.height > 100_000_000:
                raise ValueError("Image dimensions exceed the 100-megapixel safety limit.")
            image.verify()
        if not extension:
            raise ValueError("Only content-validated PNG, JPEG, GIF, and WebP images are accepted.")
        name = f"{timezone.now():%Y/%m}/{uuid.uuid4().hex}{extension}"
        destination = settings.MEDIA_ROOT / "public" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, destination)
        url = f"/media/posts/{name}"
        audit(request, "media.upload", name, size=upload.size)
        return JsonResponse({"url": url, "markdown": f"![{Path(upload.name).stem}]({url})"}, status=201)
    except (UnidentifiedImageError, OSError, ValueError) as error:
        staging.unlink(missing_ok=True)
        return JsonResponse({"error": str(error)}, status=400)


@login_required
def media_library(request):
    media_root = settings.MEDIA_ROOT / "public"
    media_root.mkdir(parents=True, exist_ok=True)
    paths = (path for path in media_root.rglob("*") if path.is_file() and not path.name.startswith("."))
    items = []
    for path in sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True):
        relative = str(path.relative_to(media_root))
        items.append({"name": path.name, "relative": relative, "url": f"/media/posts/{relative}", "size": path.stat().st_size})
    return render(request, "panel/media.html", {"items": items})


@login_required
@require_POST
def media_trash(request):
    try:
        relative = safe_relative(request.POST.get("path", ""))
        path = (settings.MEDIA_ROOT / "public").joinpath(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError("Media item does not exist.")
        item = trash_path(path, "media")
        audit(request, "media.trash", str(relative), trash_id=str(item.id))
        messages.success(request, "Media moved to 30-day trash. Existing published references will break until restored or republished.")
    except Exception as error:
        messages.error(request, str(error))
    return redirect("media_library")


@login_required
def trash(request):
    items = TrashItem.objects.filter(restored_at__isnull=True, expires_at__gt=timezone.now())
    return render(request, "panel/trash.html", {"items": items})


@login_required
@require_POST
def trash_restore(request, item_id):
    item = get_object_or_404(TrashItem, pk=item_id, restored_at__isnull=True)
    try:
        if item.kind == "post":
            source = settings.CONTENT_ROOT / item.trash_path
            destination = settings.CONTENT_ROOT / item.original_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise FileExistsError("A post with this ID already exists.")
            os.replace(source, destination)
            try:
                restored_post = get_post(destination.stem)
                restored_post.published = False
                restored_post.updated_at = timezone.now()
                raw = save_post(restored_post)
            except Exception:
                if destination.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(destination, source)
                raise
            published_trash_path = item.payload.get("published_trash_path")
            if published_trash_path:
                (settings.CONTENT_ROOT / published_trash_path).unlink(missing_ok=True)
            Revision.objects.create(kind="post", object_id=restored_post.id, label=f"Restored: {restored_post.title}", snapshot=raw, created_by=request.user)
        elif item.kind in {"file", "media"}:
            root = settings.MANAGED_ROOT if item.kind == "file" else settings.MEDIA_ROOT
            source = root / "trash" / item.trash_path
            destination = root / "public" / item.original_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise FileExistsError("The original path is occupied.")
            os.replace(source, destination)
        elif item.kind == "resource":
            resources = load_resources()
            payload = item.payload
            if payload.get("type") == "category":
                resources["categories"].append(payload["value"])
            else:
                category = next((category for category in resources["categories"] if category["id"] == payload.get("category_id")), None)
                if category is None:
                    raise ValueError("Restore the resource's category first.")
                category["entries"].append(payload["value"])
            _, raw = save_resources(resources)
            Revision.objects.create(kind="resources", object_id="resources", label="Restored trashed resource", snapshot=raw, created_by=request.user)
        item.restored_at = timezone.now()
        item.save(update_fields=["restored_at"])
        audit(request, "trash.restore", str(item.id), kind=item.kind)
        messages.success(request, "Item restored as private source/storage. Publish separately if applicable.")
    except Exception as error:
        messages.error(request, str(error))
    return redirect("trash")


@login_required
@require_POST
def trash_delete(request, item_id):
    item = get_object_or_404(TrashItem, pk=item_id, restored_at__isnull=True)
    try:
        if item.kind == "post" and item.trash_path:
            target = settings.CONTENT_ROOT / item.trash_path
            if target.exists():
                shutil.rmtree(target) if target.is_dir() else target.unlink()
            published_path = item.payload.get("published_trash_path")
            if published_path:
                (settings.CONTENT_ROOT / published_path).unlink(missing_ok=True)
        elif item.kind in {"file", "media"} and item.trash_path:
            root = settings.MANAGED_ROOT if item.kind == "file" else settings.MEDIA_ROOT
            target = root / "trash" / item.trash_path
            if target.exists():
                shutil.rmtree(target) if target.is_dir() else target.unlink()
        item.delete()
        audit(request, "trash.delete", str(item.id), kind=item.kind)
        messages.success(request, "Item permanently deleted.")
    except Exception as error:
        messages.error(request, str(error))
    return redirect("trash")
