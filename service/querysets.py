from enum import Enum

from django.db import models
from django.db.models.functions import TruncDate, TruncMonth, TruncYear, TruncDay
from pandas import DataFrame


class AnalyticsFilterBy(Enum):
    DATE = TruncDate
    MONTH = TruncMonth
    YEAR = TruncYear
    DAY = TruncDay

    @classmethod
    def from_string(cls, by: str):
        check_field = by.lower()
        if check_field not in ('day', 'month', 'year'):
            raise ValueError('this filtering not supported %s' % by)

        match check_field:
            case 'day':
                return cls.DATE
            case 'month':
                return cls.MONTH
            case 'year':
                return cls.YEAR


class BaseAnalyticsQuerySet(models.QuerySet):
    def to_df(self):
        return DataFrame(self)

    def by_dates(self, by: AnalyticsFilterBy):
        raise NotImplementedError('`by_dates()` must be implemented!')
