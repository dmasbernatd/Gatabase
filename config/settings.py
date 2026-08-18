"""Configuración de Gatabase.

Todo lo que cambia entre máquinas se lee del entorno (ver `.env.example`).
Los valores por defecto son los de desarrollo: en producción no sirven.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# El entorno real manda: `.env` solo rellena lo que no venga ya definido.
load_dotenv(BASE_DIR / ".env")


def _env(nombre, por_defecto=None):
    valor = os.environ.get(nombre, por_defecto)
    if valor is None:
        raise ImproperlyConfigured(f"Falta la variable de entorno {nombre}")
    return valor


def _env_bool(nombre, por_defecto):
    return _env(nombre, por_defecto).strip().lower() in {"1", "true", "yes", "on"}


DEBUG = _env_bool("DJANGO_DEBUG", "True")

# Con DEBUG apagado no hay clave por defecto: un despliegue sin entorno debe
# fallar al arrancar, no quedarse en marcha con la clave de desarrollo.
CLAVE_DE_DESARROLLO = "insegura-solo-para-desarrollo"
SECRET_KEY = _env("DJANGO_SECRET_KEY", CLAVE_DE_DESARROLLO if DEBUG else None)
ALLOWED_HOSTS = [h for h in _env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

INSTALLED_APPS = [
    # Sin `django.contrib.admin`: sería una segunda puerta de entrada, con sus
    # propios permisos, al lado de los roles de `tenancy`.
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "apps.tenancy",
    "apps.tutors",
    "apps.patients",
    "apps.records",
    "apps.preventive",
    "apps.scheduling",
    "apps.notices",
    "apps.audit",
    "apps.imports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Después de la autenticación: la Clínica activa sale del Usuario (ADR-0003).
    "apps.tenancy.middleware.clinica_del_usuario",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
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
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.tenancy.contexto.sesion_de_clinica",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _env("POSTGRES_DB", "gatabase"),
        "USER": _env("POSTGRES_USER", "gatabase"),
        "PASSWORD": _env("POSTGRES_PASSWORD", "gatabase"),
        "HOST": _env("POSTGRES_HOST", "127.0.0.1"),
        "PORT": _env("POSTGRES_PORT", "5433"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "tenancy.Usuario"

AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]

# El Usuario entra con su correo y su contraseña, y nada más: no hay registro
# abierto — sus cuentas las crea el admin de la Clínica — ni verificación por
# correo, porque todavía no hay correo saliente (ver ticket 02).
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# No hay registro — no se enruta `account_signup` —, pero `allauth` comprueba al
# arrancar que sus campos de alta cuadren con el modelo de Usuario, y por
# omisión incluyen `username`, que aquí no existe.
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_TEMPLATE_EXTENDS = "base.html"

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "tenancy:inicio"
LOGOUT_REDIRECT_URL = "account_login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Idioma: es-CL es el idioma de origen; aun así todo texto pasa por gettext,
# para que añadir otro idioma no obligue a reescribir plantillas.
LANGUAGE_CODE = "es-cl"
LANGUAGES = [("es-cl", "Español (Chile)")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True

# Las horas se almacenan en UTC y se presentan en la zona de la clínica.
TIME_ZONE = "America/Santiago"
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
