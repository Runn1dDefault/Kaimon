from django.conf import settings
from django.views.decorators.cache import cache_page


class CachingMixin:
    cache_timeout = settings.PAGE_CACHED_SECONDS  # Default cache timeout in seconds

    @classmethod
    def as_view(cls, *args, **kwargs):
        view = super().as_view(*args, **kwargs)
        return cache_page(cls.cache_timeout)(view)
