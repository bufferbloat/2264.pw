import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from django.conf import settings


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def atomic_write(path, value, mode=0o640):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def clean_slug(value):
    value = value.strip().lower()
    if not SLUG_RE.fullmatch(value) or len(value) > 120:
        raise ValueError("Slug must use lowercase letters, numbers, and single hyphens.")
    return value


def clean_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


@dataclass
class Post:
    id: str
    title: str
    slug: str
    excerpt: str
    published_at: date
    updated_at: datetime
    published: bool = False
    published_slug: str = ""
    media: list = field(default_factory=list)
    body: str = ""

    @property
    def path(self):
        return settings.CONTENT_ROOT / "posts" / f"{self.id}.md"

    @property
    def public_slug(self):
        return self.published_slug if self.published and self.published_slug else self.slug

    @property
    def has_unpublished_slug(self):
        return self.published and bool(self.published_slug) and self.slug != self.published_slug

    def validate(self):
        try:
            uuid.UUID(self.id)
        except ValueError as error:
            raise ValueError("Invalid post identifier.") from error
        if not self.title.strip() or len(self.title) > 200:
            raise ValueError("Title is required and must be 200 characters or fewer.")
        self.slug = clean_slug(self.slug)
        if not self.excerpt.strip() or len(self.excerpt) > 1000:
            raise ValueError("Excerpt is required and must be 1,000 characters or fewer.")
        self.published_at = clean_date(self.published_at)
        if not isinstance(self.updated_at, datetime):
            self.updated_at = datetime.fromisoformat(str(self.updated_at))
        if not isinstance(self.media, list):
            raise ValueError("Media references must be a list.")
        return self

    def serialize(self):
        self.validate()
        metadata = {
            "id": self.id,
            "title": self.title.strip(),
            "slug": self.slug,
            "excerpt": self.excerpt.strip(),
            "published_at": self.published_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "published": bool(self.published),
            "published_slug": self.published_slug or "",
            "media": self.media,
        }
        return f"---\n{yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)}---\n{self.body.rstrip()}\n"


def parse_post(raw, expected_id=None):
    if not raw.startswith("---\n"):
        raise ValueError("Post is missing YAML front matter.")
    try:
        metadata_text, body = raw[4:].split("\n---\n", 1)
    except ValueError as error:
        raise ValueError("Post front matter is not terminated.") from error
    metadata = yaml.safe_load(metadata_text) or {}
    post = Post(
        id=str(metadata.get("id", "")),
        title=str(metadata.get("title", "")),
        slug=str(metadata.get("slug", "")),
        excerpt=str(metadata.get("excerpt", "")),
        published_at=clean_date(metadata.get("published_at")),
        updated_at=datetime.fromisoformat(str(metadata.get("updated_at"))),
        published=bool(metadata.get("published", False)),
        published_slug=str(metadata.get("published_slug", "")),
        media=list(metadata.get("media") or []),
        body=body.rstrip(),
    ).validate()
    if expected_id and post.id != expected_id:
        raise ValueError("Post ID does not match its filename.")
    return post


def list_posts(strict=False):
    posts = []
    root = settings.CONTENT_ROOT / "posts"
    root.mkdir(parents=True, exist_ok=True)
    for path in root.glob("*.md"):
        try:
            posts.append(parse_post(path.read_text(encoding="utf-8"), path.stem))
        except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
            if strict:
                raise ValueError(f"Cannot publish invalid post source {path.name}: {error}") from error
    return sorted(posts, key=lambda item: (item.published_at, item.updated_at), reverse=True)


def get_post(post_id):
    try:
        normalized = str(uuid.UUID(str(post_id)))
    except ValueError as error:
        raise FileNotFoundError from error
    path = settings.CONTENT_ROOT / "posts" / f"{normalized}.md"
    return parse_post(path.read_text(encoding="utf-8"), normalized)


def save_post(post):
    post.validate()
    duplicates = [item for item in list_posts() if item.slug == post.slug and item.id != post.id]
    if duplicates:
        raise ValueError("Another post already uses this slug.")
    if post.slug in load_redirects():
        raise ValueError("This slug is reserved by a permanent redirect and cannot be reused.")
    raw = post.serialize()
    atomic_write(post.path, raw)
    return raw


def published_post_path(post_id):
    return settings.CONTENT_ROOT / "published" / "posts" / f"{post_id}.md"


def save_published_post(post):
    if not post.published or post.published_slug != post.slug:
        raise ValueError("A published snapshot must use its current public slug.")
    raw = post.serialize()
    atomic_write(published_post_path(post.id), raw)
    return raw


def list_published_posts(strict=True):
    posts = []
    root = settings.CONTENT_ROOT / "published" / "posts"
    root.mkdir(parents=True, exist_ok=True)
    for path in root.glob("*.md"):
        try:
            post = parse_post(path.read_text(encoding="utf-8"), path.stem)
            if not post.published or post.published_slug != post.slug:
                raise ValueError("snapshot is not marked as published at its current slug")
            posts.append(post)
        except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
            if strict:
                raise ValueError(f"Cannot publish invalid post snapshot {path.name}: {error}") from error
    return sorted(posts, key=lambda item: (item.published_at, item.updated_at), reverse=True)


def default_resources():
    return {"title": "resources", "description": "valuable resources i find interesting, covering a variety of fields..", "categories": []}


def validate_resources(data):
    if not isinstance(data, dict) or not isinstance(data.get("categories"), list):
        raise ValueError("Resources must contain a categories list.")
    seen_categories = set()
    seen_entries = set()
    normalized = {
        "title": str(data.get("title", "resources")).strip()[:100],
        "description": str(data.get("description", "")).strip()[:1000],
        "categories": [],
    }
    for category_order, category in enumerate(data["categories"]):
        category_id = str(category.get("id") or uuid.uuid4())
        uuid.UUID(category_id)
        if category_id in seen_categories:
            raise ValueError("Duplicate category ID.")
        seen_categories.add(category_id)
        result_category = {
            "id": category_id,
            "name": str(category.get("name", "")).strip()[:100],
            "description": str(category.get("description", "")).strip()[:500],
            "order": category_order,
            "visible": bool(category.get("visible", True)),
            "color": str(category.get("color", "#71717a")).strip(),
            "entries": [],
        }
        if not result_category["name"]:
            raise ValueError("Every category needs a name.")
        if not COLOR_RE.fullmatch(result_category["color"]):
            raise ValueError("Category color must be a six-digit hexadecimal value.")
        result_category["color"] = result_category["color"].lower()
        for entry_order, entry in enumerate(category.get("entries", [])):
            entry_id = str(entry.get("id") or uuid.uuid4())
            uuid.UUID(entry_id)
            if entry_id in seen_entries:
                raise ValueError("Duplicate resource ID.")
            seen_entries.add(entry_id)
            url = str(entry.get("url", "")).strip()
            parts = urlsplit(url)
            if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
                raise ValueError(f"Resource URL must be HTTP or HTTPS: {url or '(empty)'}")
            title = str(entry.get("title", "")).strip()[:200]
            if not title:
                raise ValueError("Every resource needs a title.")
            result_category["entries"].append({
                "id": entry_id,
                "title": title,
                "url": url,
                "description": str(entry.get("description", "")).strip()[:1000],
                "order": entry_order,
                "visible": bool(entry.get("visible", True)),
            })
        normalized["categories"].append(result_category)
    return normalized


def load_resources():
    path = settings.CONTENT_ROOT / "resources.json"
    if not path.exists():
        return default_resources()
    return validate_resources(json.loads(path.read_text(encoding="utf-8")))


def save_resources(data):
    normalized = validate_resources(data)
    raw = json.dumps(normalized, ensure_ascii=False, indent=2) + "\n"
    atomic_write(settings.CONTENT_ROOT / "resources.json", raw)
    return normalized, raw


def published_resources_path():
    return settings.CONTENT_ROOT / "published" / "resources.json"


def save_published_resources(data):
    normalized = validate_resources(data)
    raw = json.dumps(normalized, ensure_ascii=False, indent=2) + "\n"
    atomic_write(published_resources_path(), raw)
    return normalized, raw


def load_published_resources():
    path = published_resources_path()
    if not path.is_file():
        raise ValueError("Published resources snapshot is missing.")
    return validate_resources(json.loads(path.read_text(encoding="utf-8")))


def initialize_published_sources():
    """Seed live snapshots exactly once while migrating the old static site."""
    root = settings.CONTENT_ROOT / "published"
    marker = root / ".initialized"
    if marker.exists():
        return False
    for post in list_posts(strict=True):
        if post.published:
            post.published_slug = post.slug
            save_published_post(post)
    save_published_resources(load_resources())
    atomic_write(marker, "Published snapshots initialized.\n", mode=0o640)
    return True


def load_redirects():
    path = settings.CONTENT_ROOT / "redirects.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return {clean_slug(old): clean_slug(new) for old, new in value.items()}


def register_redirect(old_slug, new_slug):
    redirects = load_redirects()
    for old, destination in list(redirects.items()):
        if destination == old_slug:
            redirects[old] = new_slug
    redirects[old_slug] = new_slug
    redirects.pop(new_slug, None)
    atomic_write(settings.CONTENT_ROOT / "redirects.json", json.dumps(redirects, indent=2, sort_keys=True) + "\n")
    return redirects
