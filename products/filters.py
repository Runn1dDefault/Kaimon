from django.db.models import Subquery
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import BaseFilterBackend

from .models import Category


class CategoryLevelFilter(BaseFilterBackend):
    query_param = "level"
    description = _("Filter by categories level")

    def filter_queryset(self, request, queryset, view):
        level = request.query_params.get('level')
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
        popular_value = getattr(request, self.popular_param, '')
        if popular_value != 1:
            return queryset

        orders = ('-avg_rating', '-reviews_count', '-site_rating_count', '-site_avg_rating')
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
