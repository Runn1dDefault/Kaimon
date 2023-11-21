from django.conf import settings
from django.core.cache import caches
from django.views.decorators.cache import cache_page


class CurrencyMixin:
    def get_currency(self):
        return self.request.query_params.get(settings.CURRENCY_QUERY_PARAM, 'yen')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.setdefault('currency', self.get_currency())
        return context


class CachingMixin:
    cache_timeout = settings.PAGE_CACHED_SECONDS
    cache_name = 'pages_cache'

    @classmethod
    def get_cache_prefix(cls) -> str:
        return cls.__name__.lower()

    @classmethod
    def as_view(cls, *args, **kwargs):
        view = super().as_view(*args, **kwargs)
        return cache_page(cls.cache_timeout, cache=cls.cache_name, key_prefix=cls.get_cache_prefix())(view)

    @classmethod
    def cache_clear(cls):
        cache = caches[cls.cache_name]
        cache.delete_pattern(f'{cls.get_cache_prefix()}*')
