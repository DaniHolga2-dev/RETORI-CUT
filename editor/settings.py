
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_booleano(nombre, valor_por_defecto=False):
    valor = os.environ.get(nombre)

    if valor is None:
        return valor_por_defecto

    return valor.strip().lower() in ("1", "true", "yes", "on")


def obtener_lista(nombre):
    valor = os.environ.get(nombre, "")

    return [
        elemento.strip()
        for elemento in valor.split(",")
        if elemento.strip()
    ]


# ============================================================
# SEGURIDAD Y ENTORNO
# ============================================================

EN_RENDER = bool(os.environ.get("RENDER"))

DEBUG = obtener_booleano(
    "DEBUG",
    valor_por_defecto=not EN_RENDER,
)

SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-editor-retorika-desarrollo"
    else:
        raise ImproperlyConfigured(
            "Debes configurar SECRET_KEY en las variables de entorno."
        )


ALLOWED_HOSTS = obtener_lista("ALLOWED_HOSTS")

if EN_RENDER:
    render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

    if render_hostname:
        ALLOWED_HOSTS.append(render_hostname)

if DEBUG:
    ALLOWED_HOSTS.extend([
        "localhost",
        "127.0.0.1",
        "[::1]",
    ])

ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS))


# ============================================================
# APLICACIONES
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "reels",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URLS Y PLANTILLAS
# ============================================================

ROOT_URLCONF = "editor.urls"

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
# ============================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# ARCHIVOS MULTIMEDIA
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = Path(
    os.environ.get(
        "MEDIA_ROOT",
        str(BASE_DIR / "media"),
    )
)


# ============================================================
# ALMACENAMIENTO DE ARCHIVOS
# ============================================================
# default: vídeos, imágenes y archivos subidos.
# staticfiles: CSS, JavaScript e imágenes estáticas.
#
# IMPORTANTE:
# Django necesita ambas configuraciones.

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}


# ============================================================
# LÍMITES DE SUBIDA
# ============================================================

DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024


# ============================================================
# CSRF
# ============================================================

CSRF_TRUSTED_ORIGINS = obtener_lista(
    "CSRF_TRUSTED_ORIGINS"
)

if EN_RENDER:
    render_hostname = os.environ.get(
        "RENDER_EXTERNAL_HOSTNAME"
    )

    if render_hostname:
        origen_render = f"https://{render_hostname}"

        if origen_render not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origen_render)


# ============================================================
# CONFIGURACIÓN HTTPS Y SEGURIDAD
# ============================================================

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SECURE = not DEBUG

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"


# ============================================================
# CLAVES PRIMARIAS
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
