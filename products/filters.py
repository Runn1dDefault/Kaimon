from django.db.models import Subquery, Q
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.filters import BaseFilterBackend

from .models import Category, Product


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


class ProductSearchFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        search_term = request.query_params.get('search')
        if not search_term:
            raise ValidationError({'detail': "search is required!"})

        site = request.query_params.get('site', 'rakuten')
        try:
            page = abs(int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1

        try:
            limit = abs(int(request.query_params.get('page_size', 10)))
        except ValueError:
            limit = 20
        else:
            if limit > 20:
                limit = 20

        if search_term:
            offset = limit * page if page > 1 else 0
            search_term = f"%{search_term}%"
            sql = Product.objects.raw(
                """
                SELECT DISTINCT ON (p.id) p.id, p.name, p.avg_rating, p.reviews_count FROM products_product as p
                    WHERE p.id LIKE %s AND p.is_active AND p.name ILIKE %s
                    LIMIT %s OFFSET %s;
                """, [site + "%", search_term, limit, offset]
            )
            return sql
        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'search',
                'required': True,
                'in': 'query',
                'description': '',
                'schema': {
                    'type': 'string'
                }
            },
            {
                'name': 'page',
                'required': False,
                'in': 'query',
                'description': '',
                'schema': {
                    'type': 'number',
                    'default': 1
                }
            },
            {
                'name': 'page_size',
                'required': False,
                'in': 'query',
                'description': '',
                'schema': {
                    'type': 'string',
                    'default': 10
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
