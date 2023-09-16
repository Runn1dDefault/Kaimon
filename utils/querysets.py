from django.db.models import QuerySet
from pandas import DataFrame


class AnalyticsQuerySet(QuerySet):
    def to_df(self):
        return DataFrame(self)

