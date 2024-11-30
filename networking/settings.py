"""
Django settings for networking project.

This file combines configuration from environment variables with Django's default settings.
Environment variables allow for secure configuration management across different deployments.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# We'll use the newer pathlib approach instead of os.path
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# Core Django Settings
# These settings control fundamental Django behaviors and security
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY", "$0+b&i$$(%-3pmn45nii!2*l_--8u3+f@6#k@tfa++9cx3&cu0"
)
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(
    ","
)

# Security Settings
# These settings help protect your application in production
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() == "true"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",  # required by allauth
    # Third-party apps
    "crispy_forms",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # Local apps
    "networking_public",  # Must be before allauth for template precedence
    "networking_base",
    "networking_web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "networking.urls"
WSGI_APPLICATION = "networking.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Templates Configuration
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
    }
]

# Database Configuration
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Authentication Settings
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Third-Party Integration Settings
# Anthropic Settings
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Google API Settings
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Social Account Settings
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": GOOGLE_CLIENT_ID,
            "secret": GOOGLE_CLIENT_SECRET,
            "key": "",
        },
        "SCOPE": [
            "profile",
            "email",
            "openid",
            "https://www.googleapis.com/auth/contacts.readonly",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
        ],
        "AUTH_PARAMS": {
            "access_type": "offline",
        },
    }
}

# Crispy Forms Settings
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# Email Settings
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Authentication Settings
SITE_ID = 1
LOGIN_REDIRECT_URL = "networking_web:index"
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_FORMS = {
    "add_email": "networking_base.forms.AddEmailFormRespectingVerification"
}

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"

# Debug-specific settings
if DEBUG:
    DEBUG_PROPAGATE_EXCEPTIONS = True
