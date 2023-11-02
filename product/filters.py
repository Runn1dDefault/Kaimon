from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import SearchFilter, BaseFilterBackend

from .models import Product


class FilterByTag(BaseFilterBackend):
    param = 'tag_ids'
    description = _('Filter by tag ids')

    def filter_queryset(self, request, queryset, view):
        tag_ids = request.query_params.get(self.param, '').split(',')
        tag_ids = tuple(tag_id for tag_id in tag_ids if tag_id.strip())
        if tag_ids:
            paginator = view.paginator
            page_size = paginator.get_page_size(request)
            return Product.objects.raw(
                '''
                SELECT p.* FROM product_product as p
                   LEFT OUTER JOIN product_product_tags as pt ON (p.id = pt.product_id) 
                   WHERE (
                    p.availability AND p.is_active AND pt.tag_id IN %s
                    ) LIMIT %s
                ''', (tag_ids, page_size)
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
        paginator = view.paginator
        page_size = paginator.get_page_size(request)

        product_id = request.query_params.get(self.product_id_param)
        if product_id:
            return Product.objects.raw(
                '''
                SELECT p.* FROM product_product as p
                   LEFT OUTER JOIN product_product_genres as pg ON (p.id = pg.product_id) 
                   LEFT OUTER JOIN product_product_tags as pt ON (p.id = pt.product_id) 
                   WHERE (
                    p.availability AND p.is_active AND NOT (p.id = %s) 
                    AND (
                        pg.genre_id IN (
                            SELECT g.id FROM product_genre as g 
                            INNER JOIN product_product_genres as gp ON (g.id = gp.genre_id) 
                            WHERE (NOT (g.level IN (0, 1) AND g.level IS NOT NULL) AND gp.product_id = %s)
                            ORDER BY g.level DESC LIMIT 1
                        ) 
                        OR pt.tag_id IN (
                            SELECT t.id FROM product_tag as t 
                            INNER JOIN product_product_tags as t_p ON (t.id = t_p.tag_id) 
                            WHERE t_p.product_id = %s
                            )
                        )
                    ) LIMIT %s
                ''', (product_id, product_id, product_id, page_size)
            )

        return Product.objects.raw(
            """
            SELECT p.*, CASE WHEN p.reviews_count > 1 THEN true 
                             WHEN p.receipts_qty > 1 THEN true 
                             ELSE false END AS in_reference FROM product_product as p
                WHERE (p.availability AND p.is_active) 
                ORDER BY in_reference ASC, p.avg_rank DESC
                LIMIT %s
            """, (page_size,)
        )

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

    def get_popular_param(self, request, view):
        return request.query_params.get(self.popular_param, '0')

    def ordering_included(self, request, view) -> bool:
        popular_param = self.get_popular_param(request, view)
        if popular_param == '1':
            return True
        return False

    def filter_queryset(self, request, queryset, view):
        if self.ordering_included(request, view):
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
