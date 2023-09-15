from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy
from rest_framework.exceptions import ValidationError

from utils.helpers import get_field_by_lang


class LangSerializerMixin:
    """
    A mixin for serializers that handle translated fields.
    """
    @cached_property
    def translate_fields(self):
        return getattr(self.Meta, 'translate_fields', [])

    def get_translate_field(self, field_name: str) -> str:
        lang = self.context.get('lang', 'ja')
        translate_field = get_field_by_lang(field_name, lang)
        if not translate_field:
            raise ValidationError({'detail': gettext_lazy('Language `%s` does not support!') % lang})
        return translate_field

    def get_extra_kwargs(self):
        # This approach is more efficient because it doesn't require you to manually manipulate the serialized data.
        # It updates the field attributes directly.
        extra_kwargs = super().get_extra_kwargs()
        for original_field in self.translate_fields:
            kwargs = extra_kwargs.get(original_field, {})
            source = kwargs.get('source', '*')
            if source == '*':
                source = original_field

            translate_field_name = self.get_translate_field(source)
            if translate_field_name == original_field:
                continue

            kwargs['source'] = translate_field_name
            extra_kwargs[original_field] = kwargs
        return extra_kwargs
