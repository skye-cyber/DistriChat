from pathlib import Path
# from decouple import config
# SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-in-production')
# DEBUG = config('DEBUG', default=True, cast=bool)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-@zf6=0u6e@u&7eh_tf8rb)zy!ou8dk3b$3meg*qnkqxtoga#az"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "192.168.43.234",
    "0.0.0.0",
    "central.chatserver.local",
]


# Application definition

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_browser_reload",
    "widget_tweaks",
    # Third party apps
    "channels",
    # Local apps
    "users",
    "chat",
    "nodes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "nodes.middleware.NodePeerSyncMiddleware",
    "nodes.middleware.NodeUserAutoSyncMiddleware",
    "nodes.middleware.NodeSessionAutoSyncMiddleware",
]

ROOT_URLCONF = "districhat.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "districhat.context_processors.messages",
            ],
        },
    },
]

AUTH_USER_MODEL = "users.CustomUser"

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "users.backends.EmailBackend",
]
IS_CENTRAL_SERVER = True

# WSGI and ASGI configuration
WSGI_APPLICATION = "districhat.wsgi.application"
ASGI_APPLICATION = "districhat.asgi.application"

# Channel layers for WebSockets
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
TESTING = False
if TESTING:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "central_db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "districhat_central",
            "USER": "districhat_user",
            "PASSWORD": "districhat@PhantomJoker@15",
            "HOST": "localhost",
            "PORT": "3306",
        }
    }

"""
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "echoverse",
            "PASSWORD": "echoverse@skye@dragon17",
            "USER": "echoverseuser",
            "HOST": "127.0.0.1",
            "PORT": "5432",
        }
    }
"""

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Nairobi"

USE_I18N = True

USE_TZ = True


# Login URLs
LOGIN_REDIRECT_URL = "dashboard"
LOGIN_URL = "/accounts/login"
LOGOUT_REDIRECT_URL = "index"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

# APPEND_SLASH = False
# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"


STATICFILES_FINDERS = [
    # finds files in STATICFILES_DIRS
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",  # finds static/ in each app
    # "compressor.finders.CompressorFinder",  # keeps compressor integration
]

# Media settings for file uploads
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

UPLOAD_URL = "/uploads/"
UPLOAD_PATH = BASE_DIR / "uploads"

DOCUMENT_URL = "documents"
DOCUMENTS_ROOT = BASE_DIR / "documents"


# email verification
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587  # Commonly used ports are 587 (TLS) or 465 (SSL)
EMAIL_USE_TLS = True  # Set to True for port 587, False for port 465
# EMAIL_USE_SSL = False  # Set to True for port 465, False for port 587
EMAIL_HOST_USER = "districhat.tech@gmail.com"

EMAIL_HOST_PASSWORD = "vkcjyzwbzlgbwgzz"


# Central server URL
CENTRAL_SERVER_URL = "http://localhost:8001"


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "error.log",
            "formatter": "verbose",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}
