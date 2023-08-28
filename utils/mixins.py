from typing import Iterable

from django.conf import settings
from django.utils.translation import gettext_lazy
from rest_framework import serializers

from product.utils import get_field_by_lang


class LanguageMixin:

    def get_lang(self):
        return self.request.query_params.get(settings.LANGUAGE_QUERY, 'ja')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['lang'] = self.get_lang()
        return context


class LangSerializerMixin:
    @property
    def lang_fields(self) -> Iterable:
        meta = getattr(self, 'Meta', None)
        return getattr(meta, 'translate_fields', [])

    def get_lang(self) -> str:
        return self.context.get('lang', 'ja')

    def get_field_by_lang(self, field_name: str):
        if field_name not in self.lang_fields:
            return field_name
        return self.get_translate_field(field_name)

    def get_translate_field(self, field_name: str) -> str:
        lang = self.get_lang()
        translate_field = get_field_by_lang(field_name, lang)
        if not translate_field:
            raise serializers.ValidationError({'detail': gettext_lazy('Language %s does not support!') % lang})
        return translate_field

    def valid_translate_instance(self, instance):
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        for field in self.lang_fields or []:
            if field not in representation.keys():
                continue

            old_value = representation.pop(field)
            field_name = self.get_field_by_lang(field)
            representation[field_name] = getattr(self.valid_translate_instance(instance), field_name, None) or old_value
        return representation
