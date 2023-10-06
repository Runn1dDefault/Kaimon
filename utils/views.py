from django.conf import settings
from django.views.decorators.cache import cache_page


class LanguageMixin:

    def build_translate_field(self, field: str):
        lang = self.get_lang()
        return '%s_%s' % (field, lang) if lang != 'ja' else field

    def get_lang(self):
        return self.request.query_params.get(settings.LANGUAGE_QUERY_PARAM, 'ja')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['lang'] = self.get_lang()
        return context


class CachingMixin:
    cache_timeout = settings.PAGE_CACHED_SECONDS  # Default cache timeout in seconds

    @classmethod
    def as_view(cls, *args, **kwargs):
        view = super().as_view(*args, **kwargs)
        return cache_page(cls.cache_timeout)(view)
