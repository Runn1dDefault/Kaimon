from django.db.models import Subquery
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import BaseFilterBackend

from .models import Product, Genre


class FilterByTag(BaseFilterBackend):
    param = 'tag_ids'
    description = _('Filter by tag ids')

    def filter_queryset(self, request, queryset, view):
        tag_ids = tuple(tag_id for tag_id in request.query_params.get(self.param, '').split(',') if tag_id.strip())
        if tag_ids:
            lookup_kwarg_field = view.lookup_url_kwarg or view.lookup_field
            paginator = view.paginator
            page_size = paginator.get_page_size(request)
            check_field = f"p.{view.lookup_field}" if view.lookup_field else 1
            check_value = view.kwargs[lookup_kwarg_field] if view.lookup_field else 1
            return Product.objects.raw(
                '''
                SELECT p.* FROM product_product as p
                   LEFT OUTER JOIN product_product_tags as pt ON (p.id = pt.product_id) 
                   WHERE (
                    p.availability AND p.is_active AND pt.tag_id IN %s
                    AND %s = %s
                    ) LIMIT %s
                ''', (tag_ids, page_size, check_field, check_value)
            )
        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.param,
                'required': False,
                'in': 'query',
                'description': force_str(self.description),
                'schema': {
                    'type': 'string',
                }
            }
        ]


class ProductReferenceFilter(BaseFilterBackend):
    min_filter_qty = 1
    reference_qty = 10
    product_id_param = 'product_id'
    product_id_description = _('Recommendations by product meta')

    def filter_queryset(self, request, queryset, view):
        product_id = request.query_params.get(self.product_id_param)
        orders = ('-receipts_qty', '-reviews_count', '-avg_rank')
        if product_id:
            genre = Subquery(
                Genre.objects.filter(products__id=product_id)
                             .order_by('-level').values('id')[:1]
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


class PopularProductOrdering(BaseFilterBackend):
    popular_param = 'popular'
    popular_description = _("Ordering by popular (enabled when equal to 1)")

    def get_popular_param(self, request):
        return request.query_params.get(self.popular_param, '0')

    def ordering_included(self, request) -> bool:
        popular_param = self.get_popular_param(request)
        if popular_param == '1':
            return True
        return False

    def filter_queryset(self, request, queryset, view):
        if self.ordering_included(request):
            return queryset.order_by("-receipts_qty", "-avg_rank")
        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.popular_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.popular_description),
                'schema': {
                    'type': 'number',
                }
            }
        ]


class GenreLevelFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        level = request.query_params.get('level', 1)
        filter_kwargs = dict(level=level)
        return queryset.filter(**filter_kwargs)
