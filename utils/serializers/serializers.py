import calendar
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pandas as pd
from django.utils.timezone import localtime, now
from django.utils.translation import gettext_lazy as _
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
        fields = ('start', 'end', 'filter_by')
        hide_fields = ()
        empty_data_template = {}

    def save(self, **kwargs):
        return None

    def update(self, instance, validated_data):
        return None

    def create(self, validated_data):
        return None

    def validate_filter_by(self, filter_by: str):
        try:
            return AnalyticsFilter.get_by_string(filter_by)
        except ValueError as e:
            raise ValidationError({'filter_by': _(str(e))})

    def validate_start(self, start: datetime.date):
        today = localtime(now()).date()
        if start > today:
            raise ValidationError({'start': _(f'Cannot be grater than {today}')})
        return start

    def validate_end(self, end: datetime.date):
        today = localtime(now()).date()
        if end > today:
            return today
        return end

    def validate(self, attrs):
        start, end = attrs['start'], attrs['end']
        if start >= end:
            raise ValidationError({'start': _(f'Cannot be equal or grater than {end}')})
        return attrs

    def filtered_analytics(self, start, end, filter_by) -> AnalyticsQuerySet:
        raise NotImplementedError('`filter_queryset` must be implemented!')

    @property
    def data(self):
        start, end = self.validated_data['start'], self.validated_data['end']
        filter_by = self.validated_data['filter_by']
        analytics = self.filtered_analytics(start, end, filter_by)
        df = analytics.to_df() if analytics.exists() else pd.DataFrame()
        return ReturnDict(self.to_representation(df), serializer=self)

    @property
    def empty_data_template(self):
        return getattr(self.Meta, 'empty_data_template', {})

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
                template = deepcopy(self.empty_data_template)
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
        return df.to_dict('index')
