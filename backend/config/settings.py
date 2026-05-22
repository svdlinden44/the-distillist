import os
from datetime import timedelta
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-change-me-in-production",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = ["*"]

_csrf_defaults = "https://thedistillist.com,https://www.thedistillist.com,https://api.thedistillist.com"
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", _csrf_defaults).split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "corsheaders",
    "storages",
    "imagekit",
    "rest_framework",
    "rest_framework_simplejwt",
    "accounts",
    "cocktails",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database — Railway injects DATABASE_URL when Postgres is linked.
# Prefer private networking URL when Railway exposes it (faster, no public egress).
_database_url = (
    os.environ.get("DATABASE_URL", "").strip()
    or os.environ.get("DATABASE_PRIVATE_URL", "").strip()
)
if not os.environ.get("DATABASE_URL", "").strip() and os.environ.get(
    "DATABASE_PRIVATE_URL", ""
).strip():
    os.environ["DATABASE_URL"] = os.environ["DATABASE_PRIVATE_URL"].strip()
_use_postgres = _database_url.lower().startswith(
    ("postgres://", "postgresql://", "postgis://")
)

DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///db.sqlite3",
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=_use_postgres,
    )
}

if _use_postgres:
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["connect_timeout"] = int(
        os.environ.get("DATABASE_CONNECT_TIMEOUT", "10")
    )

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# ── Media / Cloudflare R2 ──
R2_BUCKET = os.environ.get("R2_BUCKET_NAME", "")
R2_ENDPOINT = os.environ.get("R2_ENDPOINT_URL", "")
R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.environ.get("R2_SECRET_KEY", "")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "")

_use_r2 = all([R2_BUCKET, R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY])

_staticfiles_backend = (
    "whitenoise.storage.CompressedStaticFilesStorage"
    if DEBUG
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

if _use_r2:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": R2_BUCKET,
                "endpoint_url": R2_ENDPOINT,
                "access_key": R2_ACCESS_KEY,
                "secret_key": R2_SECRET_KEY,
                "default_acl": "public-read",
                "signature_version": "s3v4",
                "object_parameters": {
                    "CacheControl": "public, max-age=86400",
                },
            },
        },
        "staticfiles": {
            "BACKEND": _staticfiles_backend,
        },
    }
    MEDIA_URL = f"{R2_PUBLIC_URL}/" if R2_PUBLIC_URL else f"{R2_ENDPOINT}/{R2_BUCKET}/"
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": _staticfiles_backend,
        },
    }
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# Dev: serve static from finders without requiring collectstatic (production still uses release build).
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_AUTOREFRESH = DEBUG

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

_cors_defaults = (
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:5173,http://127.0.0.1:5173,"
    "https://thedistillist.com,https://www.thedistillist.com"
)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", _cors_defaults).split(",")
    if origin.strip()
]
CORS_EXPOSE_HEADERS = ["X-Preview-Pipeline"]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": False,
}

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()

# Sign in with Apple — Services ID (same as frontend VITE_APPLE_CLIENT_ID).
APPLE_CLIENT_ID = os.environ.get("APPLE_CLIENT_ID", "").strip()

# Facebook Login — app credentials for Graph API token checks (same app as frontend).
FACEBOOK_APP_ID = os.environ.get("FACEBOOK_APP_ID", "").strip()
FACEBOOK_APP_SECRET = os.environ.get("FACEBOOK_APP_SECRET", "").strip()
