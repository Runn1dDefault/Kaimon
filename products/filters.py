from django.db.models import Subquery
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.filters import BaseFilterBackend

from .models import Site, Category


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
    product_id_param = 'product_id'
    product_id_description = _('Recommendations by product meta')

    def filter_queryset(self, request, queryset, view):
        product_id = request.query_params.get(self.product_id_param)
        orders = ('-site_rating_count', '-site_avg_rating')
        if product_id:
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
                'name': self.product_id_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.product_id_description),
                'schema': {
                    'type': 'string',
                }
            }
        ]
