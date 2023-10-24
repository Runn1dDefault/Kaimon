from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.fields import is_simple_callable

from language.models import LanguageModel


class TranslateField(serializers.RelatedField):
    default_error_messages = {
        'required': _('This field is required.'),
        'does_not_exist': _('Invalid language "{language}" - object does not exist.'),
        'incorrect_type': _('Incorrect type. Expected pk value, received {data_type}.'),
    }

    def __init__(self, related_field: str = 'translations', source_lang: str = None, **kwargs):
        self.related_field = related_field
        self.source_lang = source_lang
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        assert hasattr(instance, self.related_field)
        attribute_instance = getattr(instance, self.related_field).filter(language_code=self.language_code).first()
        if not attribute_instance:
            return "No translation available"

        value = attribute_instance.serializable_value(self.source_attrs[-1])
        if is_simple_callable(value):
            value = value()
        return value

    @property
    def language_code(self):
        if self.source_lang is not None:
            return self.source_lang
        return self.context.get('lang', LanguageModel.SupportLanguage.ja)

    def to_internal_value(self, data):
        try:
            obj = self.get_queryset().filter(language_code=self.language_code).first()
        except (TypeError, ValueError):
            self.fail('invalid')
        else:
            if obj is None:
                self.fail('does_not_exist', language=self.language_code, value=smart_str(data))
            return obj

    def to_representation(self, value):
        return value
