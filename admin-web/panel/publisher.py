import fcntl
import json
import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager, suppress
from datetime import timezone
from pathlib import Path

import bleach
import markdown
from django.conf import settings
from django.template.loader import render_to_string

from .content import list_published_posts, load_published_resources


ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
    "p", "br", "img", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "code",
    "blockquote", "hr", "table", "thead", "tbody", "tr", "th", "td", "del",
}
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "code": ["class"],
}

# Routes produced by the publisher or represented by the existing public site.
# Additional root-level HTML pages are discovered from PUBLIC_HTML_ROOT below.
BASE_SITEMAP_PAGES = (
    ("/", "home"),
    ("/about", "about"),
    ("/blog", "blog"),
    ("/links/resources", "resources"),
    ("/links", "links"),
    ("/files", "files"),
    ("/krokmou", "krokmou"),
    ("/sitemap", "sitemap"),
)
SITEMAP_EXCLUDED_HTML = {"404", "blog", "index", "sitemap"}


def sitemap_pages():
    pages = [{"path": path, "label": label, "has_posts": path == "/blog"} for path, label in BASE_SITEMAP_PAGES]
    known_paths = {page["path"] for page in pages}
    html_root = getattr(settings, "PUBLIC_HTML_ROOT", Path("/srv/html"))
    try:
        candidates = sorted(html_root.glob("*.html"), key=lambda path: path.name.lower())
    except OSError:
        candidates = []
    insertion_index = next((index for index, page in enumerate(pages) if page["path"] == "/sitemap"), len(pages))
    for path in candidates:
        if path.stem in SITEMAP_EXCLUDED_HTML:
            continue
        route = f"/{path.stem}"
        if route in known_paths:
            continue
        pages.insert(insertion_index, {"path": route, "label": path.stem.replace("-", " "), "has_posts": False})
        insertion_index += 1
        known_paths.add(route)
    return pages


def render_markdown(source):
    rendered = markdown.markdown(source, extensions=["extra", "sane_lists"])
    return bleach.clean(rendered, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, protocols={"http", "https", "mailto"}, strip=True)


def render_preview(post):
    return render_to_string("publish/post.html", {"post": post, "body_html": render_markdown(post.body), "origin": settings.PUBLIC_SITE_ORIGIN})


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


@contextmanager
def publish_lock():
    settings.GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
    with open(settings.GENERATED_ROOT / ".publish.lock", "a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def prepare_release():
    root = settings.GENERATED_ROOT
    releases = root / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    release_name = uuid.uuid4().hex
    temporary = Path(tempfile.mkdtemp(prefix=f".{release_name}.", dir=releases))
    try:
        published = list_published_posts(strict=True)
        slugs = set()
        for post in published:
            if post.slug in slugs:
                raise ValueError(f"Duplicate published slug: {post.slug}")
            slugs.add(post.slug)
            _write(temporary / "blog" / f"{post.slug}.html", render_preview(post))
        _write(temporary / "blog.html", render_to_string("publish/blog.html", {"posts": published, "origin": settings.PUBLIC_SITE_ORIGIN}))
        resources = load_published_resources()
        _write(temporary / "links" / "resources.html", render_to_string("publish/resources.html", {"resources": resources, "origin": settings.PUBLIC_SITE_ORIGIN}))
        pages = sitemap_pages()
        _write(temporary / "sitemap.html", render_to_string("publish/sitemap.html", {
            "pages": pages, "posts": published, "origin": settings.PUBLIC_SITE_ORIGIN,
        }))
        _write(temporary / "sitemap.xml", render_to_string("publish/sitemap.xml", {
            "pages": pages, "posts": published, "origin": settings.PUBLIC_SITE_ORIGIN,
        }))
        manifest = {
            "release": release_name,
            "posts": [{"id": post.id, "slug": post.slug, "updated_at": post.updated_at.astimezone(timezone.utc).isoformat()} for post in published],
        }
        _write(temporary / "manifest.json", json.dumps(manifest, indent=2) + "\n")
        os.chmod(temporary, 0o755)
        final = releases / release_name
        os.replace(temporary, final)
        return final
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def activate_release(release):
    root = settings.GENERATED_ROOT
    relative = Path("releases") / release.name
    temporary_link = root / f".current.{uuid.uuid4().hex}"
    os.symlink(relative, temporary_link)
    os.replace(temporary_link, root / "current")
    # Activation is the commit point. Retention cleanup must never turn a
    # successful atomic switch into an apparent publish failure.
    with suppress(OSError):
        old_releases = (path for path in (root / "releases").iterdir() if path.is_dir())
        for old in sorted(old_releases, key=lambda path: path.stat().st_mtime, reverse=True)[5:]:
            if old.resolve() != release.resolve():
                shutil.rmtree(old, ignore_errors=True)


def publish_all():
    with publish_lock():
        release = prepare_release()
        activate_release(release)
        return release
