from django.conf import settings


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
