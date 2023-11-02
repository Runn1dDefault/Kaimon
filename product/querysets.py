from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import QuerySet, F, Count, Avg, Q
from django.db.models.functions import JSONObject, Round

from utils.querysets import AnalyticsQuerySet
from utils.types import AnalyticsFilter


class TagGroupQuerySet(QuerySet):
    def tags_list(self, tag_ids=None):
        return self.values(group_id=F('id'), group_name=F('name')).annotate(
            tags=ArrayAgg(
                JSONObject(
                    id=F('tags__id'),
                    name=F('tags__name')
                ),
                filter=Q(tags__id__in=tag_ids) if tag_ids else None,
                distinct=True  # required
            )
        )


class ReviewAnalyticsQuerySet(AnalyticsQuerySet):
    def by_dates(self, by: AnalyticsFilter):
        return self.values(date=by.value('created_at')).annotate(
            info=ArrayAgg(
                JSONObject(
                    user_id=F('user__id'),
                    email=F('user__email'),
                    name=F('user__full_name'),
                    comment=F('comment'),
                    rank=F('rank'),
                    created_at=F('created_at'),
                    is_active=F('is_active'),
                    is_read=F('is_read')
                )
            ),
            count=Count('id'),
            avg_rank=Round(Avg('rank'), precision=1)
        )
