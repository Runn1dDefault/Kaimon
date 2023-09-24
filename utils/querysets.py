from django.db.models import QuerySet
from pandas import DataFrame

from utils.types import AnalyticsFilter


class AnalyticsQuerySet(QuerySet):
    def to_df(self):
        return DataFrame(self)

    def by_dates(self, by: AnalyticsFilter):
        raise NotImplementedError('`by_dates()` must be implemented!')
