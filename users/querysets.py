from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count, F
from django.db.models.functions import JSONObject, TruncDate

from utils.querysets import AnalyticsQuerySet
from utils.types import AnalyticsFilter


class UserAnalyticsQuerySet(AnalyticsQuerySet):
    def get_joined_users_analytics(self, by: AnalyticsFilter):
        return self.values(date=by.value('date_joined')).annotate(
            users=ArrayAgg(
                JSONObject(
                    id=F('id'),
                    email=F('email'),
                    is_active=F('is_active'),
                    registration_payd=F('registration_payed'),
                    date_joined=TruncDate('date_joined'),
                    image=F('image')
                )
            ),
            count=Count('id')
        )
