import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, "1" if default else "0").lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "unsafe-development-only-key"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be configured when DEBUG is disabled")
default_hosts = "admin.2264.eu,localhost,testserver" if DEBUG else "admin.2264.eu"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", default_hosts).split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "https://admin.2264.eu").split(",") if origin.strip()]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "panel",
]

MIDDLEWARE = [
    "panel.middleware.CloudflareAccessMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "panel.middleware.AdminSecurityHeadersMiddleware",
]

ROOT_URLCONF = "webmaster.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "webmaster.wsgi.application"

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": Path(os.environ.get("ADMIN_DATABASE", "/srv/state/admin.sqlite3"))}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 14}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_NAME = "__Host-2264_admin_session"
CSRF_COOKIE_NAME = "__Host-2264_admin_csrf"
SESSION_COOKIE_SECURE = env_bool("COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env_bool("COOKIE_SECURE", True)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_AGE = int(os.environ.get("SESSION_COOKIE_AGE", "3600"))
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "owner@example.invalid").strip().lower()
CF_ACCESS_REQUIRED = env_bool("CF_ACCESS_REQUIRED", not DEBUG)
CF_ACCESS_TEAM_DOMAIN = os.environ.get("CF_ACCESS_TEAM_DOMAIN", "")
CF_ACCESS_AUD = os.environ.get("CF_ACCESS_AUD", "")
CF_ACCESS_JWKS = os.environ.get("CF_ACCESS_JWKS", "")
TOTP_ENCRYPTION_KEY = os.environ.get("TOTP_ENCRYPTION_KEY", "")
STATS_INTERNAL_URL = os.environ.get("STATS_INTERNAL_URL", "http://blog-stats:8080")
STATS_INTERNAL_TOKEN = os.environ.get("STATS_INTERNAL_TOKEN", "")

CONTENT_ROOT = Path(os.environ.get("CONTENT_ROOT", "/srv/content"))
GENERATED_ROOT = Path(os.environ.get("GENERATED_ROOT", "/srv/generated"))
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "/srv/media"))
MANAGED_ROOT = Path(os.environ.get("MANAGED_ROOT", "/srv/managed"))
BACKUP_ROOT = Path(os.environ.get("BACKUP_ROOT", "/srv/backups"))
PUBLIC_SITE_ORIGIN = os.environ.get("PUBLIC_SITE_ORIGIN", "https://2264.eu").rstrip("/")
PUBLIC_HTML_ROOT = Path(os.environ.get("PUBLIC_HTML_ROOT", "/srv/html"))
UPLOAD_CHUNK_SIZE = 16 * 1024 * 1024
MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE", str(10 * 1024**3)))
MIN_FREE_BYTES = int(os.environ.get("MIN_FREE_BYTES", str(10 * 1024**3)))
MAX_IMAGE_SIZE = int(os.environ.get("MAX_IMAGE_SIZE", str(25 * 1024**2)))
TRASH_DAYS = int(os.environ.get("TRASH_DAYS", "30"))
DATA_UPLOAD_MAX_MEMORY_SIZE = UPLOAD_CHUNK_SIZE + 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_IMAGE_SIZE

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
