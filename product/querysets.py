from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import QuerySet, F
from django.db.models.functions import JSONObject


class GenreQuerySet(QuerySet):
    def get_child_products(self):
        return

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
