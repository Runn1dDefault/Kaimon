from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import QuerySet, F, Count, Avg, Q
from django.db.models.functions import JSONObject, Round

from utils.querysets import AnalyticsQuerySet
from utils.types import AnalyticsFilter


class TagGroupQuerySet(QuerySet):
    def groups_with_tags(self):
        return self.annotate(tags_qty=Count('tags__id')).filter(tags_qty__gt=0)

    def tags_list(self, name_field: str = 'name', tag_ids=None):
        return self.values(group_id=F('id'), group_name=F(name_field)).annotate(
            tag_info=ArrayAgg(
                JSONObject(
                    id=F('tags__id'),
                    name=F('tags__' + name_field)
                ), filter=Q(tags__id__in=tag_ids) if tag_ids else None
            )
        )


class GenreQuerySet(QuerySet):
    def genre_info_with_relations(self, name_field: str = 'name'):
        return self.values(
            genre_id=F('id'),
            genre_level=F('level'),
            genre_name=F(name_field)
        ).annotate(
            parents=ArrayAgg(
                JSONObject(
                    genre_id=F('parents__parent__id'),
                    genre_level=F('parents__parent__level'),
                    genre_name=F('parents__parent__' + name_field)
                ), distinct=True
            ),
            children=ArrayAgg(
                JSONObject(
                    genre_id=F('children__child__id'),
                    genre_level=F('children__child__level'),
                    genre_name=F('children__child__' + name_field)
                ), distinct=True
            ),
        )


class ProductQuerySet(QuerySet):
    def order_by_popular(self):
        return self.annotate(
            avg_rank=Avg('reviews__rank', filter=Q(reviews__is_active=True)),
            receipts_qty=Count('receipts__order_id', distinct=True)
        ).order_by('receipts_qty', 'avg_rank')


class ReviewAnalyticsQuerySet(AnalyticsQuerySet):
    def by_dates(self, by: AnalyticsFilter):
        return self.values(date=by.value('created_at')).annotate(
            info=ArrayAgg(
                JSONObject(
                    user_id=F('user__id'),
                    user_email=F('user__email'),
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
