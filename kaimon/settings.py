from datetime import timedelta
from pathlib import Path

from decouple import config
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = [
    "kaimono.vip",
    "109.123.237.209"
]
CSRF_TRUSTED_ORIGINS = [
    "https://kaimono.vip",
    "http://109.123.237.209:9010",
    "http://localhost:9010"
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
    'django_celery_beat',
    'drf_spectacular',

    'service',
    'users',
    'products',
    'promotions',
    'orders',
    'external_admin'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

GZIP_COMPRESS_CONTENT_TYPES = ['application/json']

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

DATABASES = {
    "default": {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('PRIMARY_DB'),
        'USER': config('PRIMARY_USER'),
        'PASSWORD': config('PRIMARY_PASSWORD'),
        'HOST': config('PRIMARY_HOST'),
        'PORT': config('PRIMARY_PORT', cast=int)
    },
    # "replica1": {
    #     "ENGINE": 'django.db.backends.postgresql',
    #     "NAME": config('REPLICATION1_DB'),
    #     "USER": config('REPLICATION1_USER'),
    #     "PASSWORD": config('REPLICATION1_PASSWORD'),
    #     'HOST': config('REPLICATION1_HOST'),
    #     'PORT': config('REPLICATION1_PORT', cast=int)
    # },
    # "replica2": {
    #     "ENGINE": 'django.db.backends.postgresql',
    #     "NAME": config('REPLICATION2_DB'),
    #     "USER": config('REPLICATION2_USER'),
    #     "PASSWORD": config('REPLICATION2_PASSWORD'),
    #     'HOST': config('REPLICATION2_HOST'),
    #     'PORT': config('REPLICATION2_PORT', cast=int)
    # }
}

# CONN_MAX_AGE = 300
# DATABASE_ROUTERS = ["kaimon.routers.PrimaryReplicaRouter"]

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
        "LOCATION": REDIS_CONNECTION_URL + '/0'
    },
    "users": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CONNECTION_URL + '/1'
    },
    "scraping": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CONNECTION_URL + '/2'
    },
    "pages_cache": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CONNECTION_URL + '/3'
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
CELERY_BEAT_SCHEDULER = "kaimon.schedulers.MyDatabaseScheduler"

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
    'TEST_REQUEST_DEFAULT_FORMAT': 'json'
}

CORS_ALLOWED_ORIGINS = [
    "https://kaimono.vip",
    "http://localhost:3000",  # TODO: delete after testing
    "http://109.123.237.209:9010"
]
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
MAILING_TEMPLATE = {
    "preheader": "kaimono.vip",
    "subject": "Notification",
    "content": "",
    "warning_text": "if it wasn't you. Please ignore this message and do not share the code with anyone."
}

MAILING_PLAIN_TEXT = """
*{subject}*

**********
*{content}*
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
EMAIL_CONFIRM_CODE_LIVE = 1200

CURRENCY_QUERY_PARAM = 'currency'
CURRENCY_QUERY_SCHEMA_PARAM = OpenApiParameter(
    name=CURRENCY_QUERY_PARAM,
    type=OpenApiTypes.STR,
    required=False,
    default='yen'
)

FEDEX_CLIENT_ID = 'l7766482a2061f4738b06386df74defc41'
FEDEX_SECRET = 'a6e57a4975074e5da35d01873355c3bc'
FEDEX_ACCOUNT_NUMBER = '515281100'
SHIPPER_POSTAL_CODE = "658-0032"
SHIPPER_CITY = "Kobe"
SHIPPER_COUNTRY_CODE = "JP"
FEDEX_DEFAULT_AVG_WEIGHT = 0.300

DEFAULT_INCREASE_PRICE_PER = 15
CRAWLER_URL = config("CRAWLER_URL")
QR_URL_TEMPLATE = config("QR_URL_TEMPLATE")
PRODUCT_URL_TEMPLATE = config("PRODUCT_URL_TEMPLATE")


# LOGGING = {
#     'version': 1,
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'loggers': {
#         'django.db.backends': {
#             'level': 'DEBUG',
#         },
#     },
#     'root': {
#         'handlers': ['console'],
#     }
# }

PAYBOX_ID = config("PAYBOX_ID")
PAYBOX_SECRET_KEY = config("PAYBOX_SECRET_KEY")
PAYBOX_SALT = config("PAYBOX_SALT")
PAYBOX_RESULT_URL = config("PAYBOX_RESULT_URL")
PAYBOX_SUCCESS_URL = config("PAYBOX_SUCCESS_URL")
PAYBOX_FAILURE_URL = config("PAYBOX_FAILURE_URL")


MONETA_MERCHANT_ID = config("MONETA_MERCHANT_ID")
MONETA_PRIVATE_KEY = config("MONETA_PRIVATE_KEY")
