import calendar
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from django.conf import settings
from django.utils.timezone import localtime, now
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from rest_framework.exceptions import ValidationError
from rest_framework.fields import DateField, ChoiceField
from rest_framework.serializers import ModelSerializer
from rest_framework.utils.serializer_helpers import ReturnDict

from utils.querysets import AnalyticsQuerySet
from utils.types import AnalyticsFilter


class AnalyticsSerializer(ModelSerializer):
    FILTER_BY = (
        ('day', 'day'),
        ('month', 'month'),
        ('year', 'year')
    )
    start = DateField(required=True, write_only=True)
    end = DateField(required=True, write_only=True)
    filter_by = ChoiceField(choices=FILTER_BY, write_only=True, required=True)

    class Meta:
        model = None
        fields = '__all__'
        hide_fields = ()
        empty_template = {}
        start_field = None
        end_field = None

    @property
    def _analytic_fields(self):
        return ['start', 'end', 'filter_by']

    def get_field_names(self, declared_fields, info):
        return self._analytic_fields + list(declared_fields.keys())

    def save(self, **kwargs):
        return None

    def update(self, instance, validated_data):
        return None

    def create(self, validated_data):
        return None

    @staticmethod
    def validate_filter_by(filter_by: str):
        try:
            return AnalyticsFilter.get_by_string(filter_by)
        except ValueError as e:
            raise ValidationError({'filter_by': _(str(e))})

    def validate(self, attrs):
        start, end = attrs['start'], attrs['end']
        if start >= end:
            raise ValidationError({'start': _(f'Cannot be equal or grater than {end}'),
                                   'end': _(f'Cannot be equal or grater than {start}')})
        today = localtime(now()).date()
        if start > today:
            raise ValidationError({'start': _(f'Cannot be grater than {today}')})
        if end > today:
            attrs['end'] = today
        return attrs

    def build_queries(self) -> dict[str, Any]:
        start_field = getattr(self.Meta, 'start_field')
        end_field = getattr(self.Meta, 'end_field')
        start, end = self.validated_data['start'], self.validated_data['end']
        queries = {start_field + '__gte': start, end_field + '__lte': end}
        extra_kwargs = self.get_extra_kwargs()

        for field in self.Meta.fields:
            source = extra_kwargs.get(field, {}).get('source', field)
            field_value = self.validated_data.get(source)
            if field_value is None:
                continue

            if isinstance(field_value, set | list):
                queries[field + '__in'] = field_value
            else:
                queries[field] = field_value
        return queries

    def _base_queryset(self):
        model = getattr(self.Meta, 'model')
        return model.analytics.filter(**self.build_queries())

    def filtered_analytics(self) -> AnalyticsQuerySet:
        filter_by = self.validated_data['filter_by']
        return self._base_queryset().by_dates(filter_by)

    @property
    def data(self):
        analytics_queryset = self.filtered_analytics()
        df = analytics_queryset.to_df() if analytics_queryset.exists() else pd.DataFrame()
        return ReturnDict(self.to_representation(df), serializer=self)

    @property
    def empty_template(self):
        return getattr(self.Meta, 'empty_template', {})

    def add_empty_rows(self, found_dates, start, end, filter_by):
        match filter_by:
            case AnalyticsFilter.MONTH:
                iters = (end.month - start.month) + 1
                iter_date = datetime(day=1, month=start.month, year=start.year, hour=0, minute=0, second=0,
                                     tzinfo=timezone.utc)
            case AnalyticsFilter.YEAR:
                iters = (end.year - start.year) + 1
                iter_date = datetime(day=1, month=1, year=start.year, hour=0, minute=0, second=0, tzinfo=timezone.utc)
            case _:
                iters = (end - start).days + 1
                iter_date = start

        not_found_dates = []
        for _ in range(iters):
            if iter_date not in found_dates:
                template = deepcopy(self.empty_template)
                template['date'] = iter_date
                not_found_dates.append(template)

            match filter_by:
                case AnalyticsFilter.MONTH:
                    _, days = calendar.monthrange(iter_date.year, iter_date.month)
                    iter_date += timedelta(days=days)
                case AnalyticsFilter.YEAR:
                    first = datetime(year=iter_date.year, day=1, month=1)
                    second = datetime(year=iter_date.year + 1, day=1, month=1)
                    iter_date += timedelta(days=(second - first).days)
                case _:
                    iter_date += timedelta(days=1)
        return not_found_dates

    @property
    def hide_fields(self):
        return getattr(self.Meta, 'hide_fields', None)

    def to_representation(self, df):
        dates = df['date'].tolist() if df.empty is False else []
        start, end = self.validated_data['start'], self.validated_data['end']
        filter_by = self.validated_data['filter_by']
        empty_rows = self.add_empty_rows(dates, start, end, filter_by)

        if empty_rows:
            df = pd.concat([df, pd.DataFrame.from_records(empty_rows)], ignore_index=True)
            df = df.sort_values(by='date')

        if df.empty is False:
            df['date'] = df['date'].apply(lambda x: str(x))
            df.set_index('date', inplace=True)

            remove_fields = [field for field in self.hide_fields or [] if field in df.columns]
            if remove_fields:
                df = df.drop(columns=list(self.hide_fields))

        rep = OrderedDict()
        rep['total_count'] = self._base_queryset().count()
        rep['data'] = df.to_dict('index')
        return rep


class LangSerializerMixin:
    """
    A mixin for serializers that handle translated fields.
    """

    @cached_property
    def translate_fields(self):
        return getattr(self.Meta, 'translate_fields', [])

    def get_translate_field(self, field_name: str) -> str:
        lang = self.context.get('lang', 'ja')
        if lang not in settings.SUPPORTED_LANG:
            raise ValidationError({'detail': _('Language `%s` does not support!') % lang})

        translate_field = f'{field_name}_{lang}' if lang != 'ja' else field_name
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
