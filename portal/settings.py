"""
Django settings for portal project.

Generated by 'django-admin startproject' using Django 3.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
import sys
import dj_database_url

from dotenv import load_dotenv

load_dotenv()

# Tests whether the second command line argument (after ./manage.py) was test
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY", "j$e+wzxdum=!k$bwxpgt!$(@6!iasecid^tqnijx@r@o-6x%6d"
)

debug = os.getenv("DJANGO_DEBUG", "False")
# DEBUG will be True if DJANGO_DEBUG exists and is "True". Else, false.
DEBUG = True if debug == "True" else False


ALLOWED_HOSTS = ["0.0.0.0", "127.0.0.1", ".herokuapp.com"]


# Application definition

INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",
    "django_sass",
    "invitations",
    "django.contrib.sites",  # Required for invitations
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "profiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "user_language_middleware.UserLanguageMiddleware",
]

ROOT_URLCONF = "portal.urls"

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

WSGI_APPLICATION = "portal.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

if TESTING:
    db_config = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
elif os.getenv("DATABASE_URL"):
    db_config = dj_database_url.config(conn_max_age=600, ssl_require=True)
else:
    db_config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "covid_portal",
        "USER": os.getenv("DATABASE_USERNAME"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD"),
        "HOST": os.getenv("DATABASE_HOST", "localhost"),
        "PORT": os.getenv("DATABASE_PORT", ""),
    }

DATABASES = {"default": db_config}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 3},
    },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGES = (
    ("en", "English"),
    ("fr", "French"),
)

LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
]

LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Application security: should be set to True in production
# https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/#https
is_prod = os.getenv("DJANGO_ENV", "development") == "production"

SECURE_SSL_REDIRECT = is_prod
SESSION_COOKIE_SECURE = is_prod
CSRF_COOKIE_SECURE = is_prod

# For sites that should only be accessed over HTTPS, instruct modern browsers to refuse to connect to your domain name via an insecure connection (for a given period of time)
SECURE_HSTS_SECONDS = 3600 if is_prod else 0

# Instructs the browser to send a full URL, but only for same-origin links. No referrer will be sent for cross-origin links.
SECURE_REFERRER_POLICY = "same-origin"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"

AUTH_USER_MODEL = "profiles.HealthcareUser"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "start"
LOGOUT_REDIRECT_URL = "landing"


# Invitations app
SITE_ID = 1  # Required for invitations app
# INVITATIONS_ACCEPT_INVITE_AFTER_SIGNUP = True
INVITATIONS_GONE_ON_ACCEPT_ERROR = False
INVITATIONS_SIGNUP_REDIRECT = "/error/"
INVITATIONS_SIGNUP_REDIRECT = "/signup/"
INVITATIONS_EMAIL_SUBJECT_PREFIX = ""
