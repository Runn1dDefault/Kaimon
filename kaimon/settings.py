from datetime import timedelta
from pathlib import Path

from decouple import config
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = True

ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",  # JS for testing
    "http://176.126.166.140:9010",
    "http://176.126.166.140",
    "http://localhost:9010",
    "http://kaimono.vip",
]
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'django_celery_beat',
    'drf_spectacular',

    'users',  # ready
    'product',  # ready
    'rakuten_scraping',  # ready
    'currencies',
    'promotions',
    'order',
    'external_admin'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'kaimon.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'kaimon.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST'),
        'PORT': config('POSTGRES_PORT', cast=int, default=5432)
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'kaimono-static/'
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_URL = 'kaimono-media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'
AUTHENTICATION_BACKENDS = ['users.backends.EmailOrUsernameAuthBackend']

# Caches
REDIS_CONNECTION_URL = config("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CONNECTION_URL + '/3'
    },
    "users": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CONNECTION_URL + '/1'
    },
    "scraping": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CONNECTION_URL + '/2'
    },
}
PAGE_CACHED_SECONDS = 21600

# Celery settings
CELERY_BROKER_URL = REDIS_CONNECTION_URL + '/0'
CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CELERY_RESULT_BACKEND = REDIS_CONNECTION_URL + '/0'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"

# Jwt
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=31),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": config('VERIFYING_KEY', default=""),
}

# drf
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "COERCE_DECIMAL_TO_STRING": False,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

CORS_ALLOW_ALL_ORIGINS = True  # TODO: off after testing

# swagger
SPECTACULAR_SETTINGS = {
    'TITLE': 'Kaimono Project API',
    'DESCRIPTION': '',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    # 'SERVE_PUBLIC': False # TODO: change after deploy
}

# Mailing settings
EMAIL_HOST = config('EMAIL_HOST')
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER')
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
RESTORE_VERIFY_TEMPLATE = {
    "subject": "Verification code",
    "code": "",
    "warning_text": "if it wasn't you. Please ignore this message and do not share the code with anyone."
}
VERIFICATION_PLAIN_TEXT = """
Verify your email
*{subject}*

**********
*{code}*
**********

Warning: {warning_text}

© Copyright Kaimono. All Rights Reserved
"""

# Custom settings
RESTORE_SETTINGS = {
    "CACHE_NAME": "users",
    "CODE_PREFIX": "restore_code:",
    "CODE_ALLOWED_CHARS": "0123456789",
    "CODE_LIVE_SECONDS": 600,
    "TOKEN_PREFIX": "restore_token:",
    "TOKEN_LEN": 6,
    "TOKEN_LIVE_SECONDS": 1200,
    "TOKEN_ALGORITHM": "HS256",
    "MAIL_SUBJECT": ""
}
EMAIL_CONFIRM_CODE_LIVE = 43200

PARSING_SETTINGS = {'CACHE_NAME': "scraping"}
INCREASE_PRICE_PERCENTAGE = 10

SUPPORTED_LANG = ('ru', 'en', 'ja', 'tr', 'ky', 'kz')
LANGUAGE_QUERY_PARAM = 'lang'
CURRENCY_QUERY_PARAM = 'currency'
LANGUAGE_QUERY_SCHEMA_PARAM = OpenApiParameter(
    name=LANGUAGE_QUERY_PARAM,
    type=OpenApiTypes.STR,
    required=False,
    default='ja'
)
CURRENCY_QUERY_SCHEMA_PARAM = OpenApiParameter(
    name=CURRENCY_QUERY_PARAM,
    type=OpenApiTypes.STR,
    required=False,
    default='yen'
)
