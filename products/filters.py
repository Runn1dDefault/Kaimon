from django.db.models import Subquery, Q
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import BaseFilterBackend

from .models import Category


class CategoryLevelFilter(BaseFilterBackend):
    query_param = "level"
    description = _("Filter by categories level")

    def filter_queryset(self, request, queryset, view):
        level = request.query_params.get(self.query_param)
        if level:
            return queryset.filter(level=level)
        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.query_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.description),
                'schema': {
                    'type': 'number',
                    'default': 1
                }
            }
        ]


class ProductReferenceFilter(BaseFilterBackend):
    description = _('Popular products ordering')
    popular_param = 'popular'

    def filter_queryset(self, request, queryset, view):
        popular_value = request.query_params.get(self.popular_param, '')
        if popular_value != '1':
            return queryset

        orders = ('-reviews_count', '-avg_rating', '-site_reviews_count', '-site_avg_rating')
        if view.detail is True:
            lookup_field = view.lookup_url_kwarg or view.lookup_field
            product_id = view.kwargs[lookup_field]
            genre = Subquery(
                Category.objects.filter(products__id=product_id)
                                .order_by('-level')
                                .values('id')[:1]
            )
            return queryset.exclude(id=product_id).filter(genres__id=genre).order_by(*orders)
        return queryset.order_by(*orders)

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.popular_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.description),
                'schema': {
                    'type': 'string',
                    'default': '0'
                }
            }
        ]


class ProductTagFilter(BaseFilterBackend):
    tag_param = "tag_ids"
    description = _("Filter by tag ids...")

    def filter_queryset(self, request, queryset, view):
        tag_ids = request.query_params.get(self.tag_param)
        if not tag_ids:
            return queryset

        tag_ids = [tag_id for tag_id in tag_ids.split(',') if tag_id.strip()]
        ids = queryset.filter(
            Q(tags__id__in=tag_ids) | Q(inventories__tags__id__in=tag_ids)
        ).values_list('id', flat=True)
        return queryset.filter(id__in=ids)

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.tag_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.description),
                'schema': {
                    'type': 'string'
                }
            }
        ]
