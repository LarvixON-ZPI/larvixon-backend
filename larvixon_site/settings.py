from datetime import timedelta
from pathlib import Path
import sys
import os
import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))

SECRET_KEY = env("SECRET_KEY", default="django-insecure-fallback-key-dla-dev")  # type: ignore

DEBUG = env("DEBUG")
IS_TESTING = "test" in sys.argv

FORCE_HTTPS = env.bool("FORCE_HTTPS", default=False)  # type: ignore

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["larvixon-backend-v1.azurewebsites.net", "127.0.0.1", "localhost"])  # type: ignore
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if DEBUG is False and not IS_TESTING:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

ML_ENDPOINT_URL: str = env("ML_ENDPOINT_URL", default="http://127.0.0.1:8001/predict")  # type: ignore

MOCK_ML: bool = env.bool("MOCK_ML", default=False)  # type: ignore

DEFAULT_PAGE_SIZE = 6

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")  # type: ignore

CELERY_RESULT_BACKEND = CELERY_BROKER_URL

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

CELERY_BEAT_SCHEDULE = {
    "cleanup-old-analyses-videos-daily": {
        "task": "analysis.tasks.cleanup_old_analyses_videos",
        "schedule": crontab(hour=0, minute=0),  # every day at midnight
    },
}

VIDEO_LIFETIME_DAYS = env.int("VIDEO_LIFETIME_DAYS", default=14)  # type: ignore

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django_filters",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "allauth.mfa",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework.authtoken",
    "drf_spectacular",
    "corsheaders",
    "accounts.apps.AccountsConfig",
    "analysis",
    "reports",
    "storages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "larvixon_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "larvixon_site.wsgi.application"


# Database
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")  # type: ignore
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Social authentication settings
SITE_ID = 1
AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": env("GOOGLE_CLIENT_ID", default=""),  # type: ignore
            "secret": env("GOOGLE_SECRET", default=""),  # type: ignore
            "key": "",
        }
    }
}

# 2FA settings
ACCOUNT_MFA_MANDATORY = True

# Internationalization
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# --- Static files (for collectstatic) ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Media files (uploaded by users) ---
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Azure Storage configuration ---
AZURE_ACCOUNT_NAME = env("AZURE_ACCOUNT_NAME", default=None)  # type: ignore
AZURE_ACCOUNT_KEY = env("AZURE_ACCOUNT_KEY", default=None)  # type: ignore
AZURE_CONTAINER = env("AZURE_CONTAINER", default=None)  # type: ignore

if DEBUG is False and AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY and AZURE_CONTAINER:
    print("--- Production Mode using Azure Blob Storage ---")
    AZURE_MEDIA_LOCATION = "media"
    AZURE_STATIC_LOCATION = "static"

    MEDIA_URL = (
        f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_MEDIA_LOCATION}/"
    )
    STATIC_URL = (
        f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_STATIC_LOCATION}/"
    )

    STORAGES = {
        # User files uploaded media
        "default": {
            "BACKEND": "storages.backends.azure_storage.AzureStorage",
            "OPTIONS": {
                "account_name": AZURE_ACCOUNT_NAME,
                "account_key": AZURE_ACCOUNT_KEY,
                "azure_container": AZURE_CONTAINER,
                "location": AZURE_MEDIA_LOCATION,
                "expiration_secs": 100,
            },
        },
        # Static files
        "staticfiles": {
            "BACKEND": "storages.backends.azure_storage.AzureStorage",
            "OPTIONS": {
                "account_name": AZURE_ACCOUNT_NAME,
                "account_key": AZURE_ACCOUNT_KEY,
                "azure_container": AZURE_CONTAINER,
                "location": AZURE_STATIC_LOCATION,
            },
        },
    }
else:
    print("--- Local Development Mode ---")
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": MEDIA_ROOT,
                "base_url": MEDIA_URL,
            },
        },
        "staticfiles": {
            "BACKEND": "django.core.files.storage.StaticFilesStorage",
            "OPTIONS": {
                "location": STATIC_ROOT,
                "base_url": STATIC_URL,
            },
        },
    }

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": "my-app-auth",
    "JWT_AUTH_HEADER_PREFIX": "Bearer",
    "JWT_AUTH_REFRESH_COOKIE": "my-refresh-token",
    "JWT_AUTH_REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# Django REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "larvixon_site.pagination.ForceHTTPSPaginator",
    "PAGE_SIZE": DEFAULT_PAGE_SIZE,
}

# Spectacular settings for API documentation
SPECTACULAR_SETTINGS = {
    "TITLE": "Larvixon Backend API",
    "DESCRIPTION": "API for larval behavior analysis system - handles user accounts, authentication, and video analysis tracking",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    "EXTENSIONS": ["drf_spectacular.extensions.DjangoFilterExtension"],
}

# JWT settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# CORS settings for Flutter app
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://127.0.0.1:3000"],  # type: ignore
)

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "content-range",
    "upload-id",
    "filename",
    "title",
]

# Custom user model
AUTH_USER_MODEL = "accounts.User"

if IS_TESTING:
    print("--- RUNNING IN TEST MODE ---")
    print("--- Overriding default storage to FileSystemStorage ---")

    MEDIA_ROOT = os.path.join(BASE_DIR, "test_media")

    STORAGES["default"] = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    }
