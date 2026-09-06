import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


DATABASE_PATH = Path(os.environ.get("BLOG_STATS_DATABASE", "/data/views.sqlite3"))
SECRET_PATH = Path(os.environ.get("BLOG_STATS_SECRET_FILE", "/data/cookie-secret"))
POSTS_DIRECTORY = Path(os.environ.get("BLOG_POSTS_DIRECTORY", "/posts"))
PORT = int(os.environ.get("BLOG_STATS_PORT", "8080"))
COOKIE_NAME = "blog_visitor"
COOKIE_MAX_AGE = 34_560_000  # 400 days, the practical browser maximum.
VIEW_PATH = re.compile(r"^/posts/([a-zA-Z0-9_-]+)/view$")
LIKE_PATH = re.compile(r"^/posts/([a-zA-Z0-9_-]+)/like$")


def load_or_create_secret():
    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        descriptor = os.open(SECRET_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, "wb") as secret_file:
            secret_file.write(secrets.token_bytes(32))

    secret = SECRET_PATH.read_bytes()
    if len(secret) < 32:
        raise RuntimeError("The cookie signing secret is invalid")
    return secret


COOKIE_SECRET = load_or_create_secret()


def connect_database():
    connection = sqlite3.connect(DATABASE_PATH, timeout=5)
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def initialize_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect_database() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS post_views (
                post_slug TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                viewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (post_slug, visitor_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS post_likes (
                post_slug TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                liked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (post_slug, visitor_id)
            )
            """
        )


def sign_visitor_id(visitor_id):
    signature = hmac.new(COOKIE_SECRET, visitor_id.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{visitor_id}.{signature}"


def validate_visitor_token(token):
    try:
        visitor_id, supplied_signature = token.split(".", 1)
    except ValueError:
        return None

    if not re.fullmatch(r"[0-9a-f]{32}", visitor_id):
        return None

    expected_signature = hmac.new(
        COOKIE_SECRET, visitor_id.encode("ascii"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return None
    return visitor_id


def get_post_stats(connection, post_slug, visitor_id):
    views = connection.execute(
        "SELECT COUNT(*) FROM post_views WHERE post_slug = ?", (post_slug,)
    ).fetchone()[0]
    likes = connection.execute(
        "SELECT COUNT(*) FROM post_likes WHERE post_slug = ?", (post_slug,)
    ).fetchone()[0]
    liked = connection.execute(
        "SELECT 1 FROM post_likes WHERE post_slug = ? AND visitor_id = ?",
        (post_slug, visitor_id),
    ).fetchone() is not None
    return {"views": views, "likes": likes, "liked": liked}


def get_all_view_counts():
    view_counts = {
        post_file.stem: 0
        for post_file in POSTS_DIRECTORY.glob("*.html")
        if re.fullmatch(r"[a-zA-Z0-9_-]+", post_file.stem)
    }
    with connect_database() as connection:
        rows = connection.execute(
            "SELECT post_slug, COUNT(*) FROM post_views GROUP BY post_slug"
        ).fetchall()

    for post_slug, views in rows:
        if post_slug in view_counts:
            view_counts[post_slug] = views
    return view_counts


def record_view(post_slug, visitor_id):
    with connect_database() as connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO post_views (post_slug, visitor_id) VALUES (?, ?)",
            (post_slug, visitor_id),
        )
        stats = get_post_stats(connection, post_slug, visitor_id)
        stats["newView"] = cursor.rowcount == 1
    return stats


def set_like(post_slug, visitor_id, liked):
    with connect_database() as connection:
        if liked:
            connection.execute(
                "INSERT OR IGNORE INTO post_likes (post_slug, visitor_id) VALUES (?, ?)",
                (post_slug, visitor_id),
            )
        else:
            connection.execute(
                "DELETE FROM post_likes WHERE post_slug = ? AND visitor_id = ?",
                (post_slug, visitor_id),
            )
        return get_post_stats(connection, post_slug, visitor_id)


class BlogStatsServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "2264BlogStats/1.2"

    def send_json(self, status, payload, visitor_token=None):
        response = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")

        if visitor_token:
            cookie = (
                f"{COOKIE_NAME}={visitor_token}; Max-Age={COOKIE_MAX_AGE}; "
                "Path=/; HttpOnly; SameSite=Lax"
            )
            if self.headers.get("X-Forwarded-Proto", "").lower() == "https":
                cookie += "; Secure"
            self.send_header("Set-Cookie", cookie)

        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/healthz":
            self.send_json(200, {"status": "ok"})
            return
        if path == "/posts/views":
            try:
                view_counts = get_all_view_counts()
            except sqlite3.Error:
                self.send_json(503, {"error": "post statistics unavailable"})
                return
            self.send_json(200, {"views": view_counts})
            return
        self.send_json(404, {"error": "not found"})

    def get_post_slug(self, path_pattern):
        path = unquote(urlsplit(self.path).path)
        match = path_pattern.fullmatch(path)
        if not match:
            self.send_json(404, {"error": "not found"})
            return None

        post_slug = match.group(1)
        if not (POSTS_DIRECTORY / f"{post_slug}.html").is_file():
            self.send_json(404, {"error": "unknown post"})
            return None
        return post_slug

    def get_visitor(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            visitor_token = cookie[COOKIE_NAME].value if COOKIE_NAME in cookie else ""
        except Exception:
            visitor_token = ""

        visitor_id = validate_visitor_token(visitor_token)
        if visitor_id is None:
            visitor_id = uuid.uuid4().hex
            visitor_token = sign_visitor_id(visitor_id)
        return visitor_id, visitor_token

    def do_POST(self):
        if self.headers.get("X-Blog-View") != "1":
            self.send_json(403, {"error": "forbidden"})
            return

        post_slug = self.get_post_slug(VIEW_PATH)
        if post_slug is None:
            return

        visitor_id, visitor_token = self.get_visitor()

        try:
            stats = record_view(post_slug, visitor_id)
        except sqlite3.Error:
            self.send_json(503, {"error": "post statistics unavailable"})
            return

        self.send_json(200, stats, visitor_token=visitor_token)

    def update_like(self, liked):
        if self.headers.get("X-Blog-Like") != "1":
            self.send_json(403, {"error": "forbidden"})
            return

        post_slug = self.get_post_slug(LIKE_PATH)
        if post_slug is None:
            return

        visitor_id, visitor_token = self.get_visitor()
        try:
            stats = set_like(post_slug, visitor_id, liked)
        except sqlite3.Error:
            self.send_json(503, {"error": "post statistics unavailable"})
            return

        self.send_json(200, stats, visitor_token=visitor_token)

    def do_PUT(self):
        self.update_like(True)

    def do_DELETE(self):
        self.update_like(False)


if __name__ == "__main__":
    initialize_database()
    server = BlogStatsServer(("0.0.0.0", PORT), RequestHandler)
    print(f"Blog statistics server listening on port {PORT}", flush=True)
    server.serve_forever()
