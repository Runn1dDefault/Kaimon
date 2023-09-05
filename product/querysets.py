from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import QuerySet, F, Count, Avg, Q
from django.db.models.functions import JSONObject


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
