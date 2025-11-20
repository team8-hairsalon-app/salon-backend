# config/settings.py
import os
from pathlib import Path
from datetime import timedelta
import dj_database_url

# Optional: load .env (pip install python-dotenv)
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

# --- Base directory ---
BASE_DIR = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

# --- Security ---
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-change-this-in-prod")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"

# On Render, set DJANGO_ALLOWED_HOSTS in the dashboard, e.g.:
# salon-backend.onrender.com
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# --- Installed apps ---
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "corsheaders",

    # Local apps
    "api",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serve static files efficiently in production (Render)
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "corsheaders.middleware.CorsMiddleware",  # must be above CommonMiddleware
    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --- Root URL ---
ROOT_URLCONF = "config.urls"

# --- Templates ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=False,
        )
    }
else:
    # fallback for CI / tests
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static files ---
STATIC_URL = "static/"

# Where collectstatic will put files on Render
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise compressed/hashed static files in production
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- Default PK field ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF / JWT ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # Public by default; views override where needed
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

# --- CORS / CSRF ---
CORS_ALLOWED_ORIGINS = [
    # Local Vite dev
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    # Production frontend on Vercel
    "https://salon-frontend-pink.vercel.app",
]

CSRF_TRUSTED_ORIGINS = [
    # Local Vite dev
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    # Production frontend on Vercel
    "https://salon-frontend-pink.vercel.app",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "Accept",
    "Accept-Encoding",
    "Authorization",
    "Content-Type",
    "Origin",
    "User-Agent",
    "DNT",
    "Cache-Control",
    "X-Requested-With",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# --- Email (dev: prints to console) ---
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@hairsalon.dev"

# --- Stripe / Frontend ---
# Read ONLY from environment variables.
# In dev: from .env
# In prod: from Render environment settings.
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Default to the deployed frontend (Vercel) in production;
# in local dev you can override with FRONTEND_BASE_URL=http://localhost:5173
FRONTEND_BASE_URL = os.getenv(
    "FRONTEND_BASE_URL",
    "https://salon-frontend-pink.vercel.app",
)

# --- Twilio (optional; leave blank in dev to no-op SMS) ---
TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
