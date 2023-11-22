from django.contrib.auth import get_user_model
from django.core.cache import caches


def smp_cache_key_for_email(email: str):
    return 'smtp:' + email


def get_sentinel_user():
    user, _ = get_user_model().objects.get_or_create(username="deleted")
    if user.is_active is True:
        user.is_active = False
        user.save()
    return user


def check_user_recovery_time(email) -> int | None:
    cache = caches['users']
    cache_key = smp_cache_key_for_email(email)
    ttl_seconds = cache.ttl(cache_key)
    match ttl_seconds:
        case -2:
            return None
        case -1:
            raise ValueError('it never expires')
        case _:
            return ttl_seconds

