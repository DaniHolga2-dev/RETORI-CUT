from pathlib import Path


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

SECRET_KEY = "django-insecure-editor-retorika-desarrollo"

DEBUG = True

ALLOWED_HOSTS = []


# ============================================================
# APLICACIONES
# ============================================================

INSTALLED_APPS = [

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # EDITOR
    "reels",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URLS
# ============================================================

ROOT_URLCONF = "editor.urls"


# ============================================================
# PLANTILLAS
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

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


# ============================================================
# WSGI
# ============================================================

WSGI_APPLICATION = "editor.wsgi.application"


# ============================================================
# BASE DE DATOS
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ============================================================
# VALIDACIÓN DE CONTRASEÑAS
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# IDIOMA Y ZONA HORARIA
# ============================================================

LANGUAGE_CODE = "es-es"

TIME_ZONE = "Europe/Madrid"

USE_I18N = True

USE_TZ = True


# ============================================================
# ARCHIVOS ESTÁTICOS
# CSS, JAVASCRIPT, IMÁGENES...
# ============================================================

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# ARCHIVOS MULTIMEDIA
# Vídeos subidos, miniaturas, audios, exportaciones...
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# CONFIGURACIÓN DE SUBIDA DE VÍDEOS
# ============================================================

# Permitimos archivos grandes durante el desarrollo.
# Más adelante controlaremos el límite desde EDITOR.

DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024


# ============================================================
# CLAVE PRIMARIA
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"