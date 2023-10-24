from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Value, F, Subquery, OuterRef, CharField, Q
from django.db.models.functions import Coalesce, JSONObject

from product.models import TagGroupTranslation, TagTranslation


def grouped_tags(group_queryset, lang: str, tag_ids=None):
    translation_not_available = Value('No translation available')

    return group_queryset.values(group_id=F('id')).annotate(
        group_name=Coalesce(
            Subquery(
                TagGroupTranslation.objects.filter(
                    group_id=OuterRef('id'),
                    language_code=lang
                ).values('name')[:1],
                output_field=CharField()
            ),
            translation_not_available
        ),
        tags=ArrayAgg(
            JSONObject(
                id=F('tags__id'),
                name=Coalesce(
                    Subquery(
                        TagTranslation.objects.filter(
                            tag_id=OuterRef('tags__id'),
                            language_code=lang
                        ).values('name')[:1],
                        output_field=CharField()
                    ),
                    translation_not_available
                ),
            ),
            filter=Q(tags__id__in=tag_ids) if tag_ids else None,
            distinct=True  # required
        )
    )
