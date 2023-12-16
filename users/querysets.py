from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count, F
from django.db.models.functions import JSONObject, TruncDate

from service.querysets import BaseAnalyticsQuerySet


class UserAnalyticsQuerySet(BaseAnalyticsQuerySet):
    def by_dates(self, by):
        return self.values(date=by.value('date_joined')).annotate(
            users=ArrayAgg(
                JSONObject(
                    id=F('id'),
                    email=F('email'),
                    is_active=F('is_active'),
                    registration_payed=F('registration_payed'),
                    email_confirmed=F('email_confirmed'),
                    date_joined=TruncDate('date_joined'),
                    image=F('image')
                )
            ),
            count=Count('id')
        )
