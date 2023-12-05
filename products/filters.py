from django.db import connection
from django.db.models import Subquery, Q, OuterRef, F
from django.db.models.functions import JSONObject
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.filters import BaseFilterBackend

from .models import ProductInventory, ProductImage


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


class ProductPopularFilter(BaseFilterBackend):
    description = _('Popular products ordering')
    popular_param = 'popular'

    def filter_queryset(self, request, queryset, view):
        popular_value = request.query_params.get(self.popular_param, '')
        if popular_value != '1':
            return queryset
        return (
            queryset.filter(site_reviews_count__gt=0, site_avg_rating__gt=0)
                    .order_by('-site_reviews_count', '-site_avg_rating')[:100]
        )

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.popular_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.description),
                'schema': {
                    'type': 'number',
                    'default': 0
                }
            }
        ]


class ProductTagFilter(BaseFilterBackend):
    tag_param = "tag_ids"

    def filter_queryset(self, request, queryset, view):
        tag_ids = request.query_params.get(self.tag_param)
        if not tag_ids:
            return queryset

        tag_ids = [tag_id for tag_id in tag_ids.split(',') if tag_id.strip()]
        ids = queryset.filter(
            Q(tags__id__in=tag_ids) | Q(inventories__tags__id__in=tag_ids)
        ).values_list('id', flat=True)
        return queryset.filter(id__in=ids)


class ProductFilter(BaseFilterBackend):
    category_param = "category_id"
    category_description = _("Filter by category...")

    product_ids_param = "product_ids"
    product_ids_description = _("Filter by product ids...")

    tag_ids_param = "tag_ids"
    tag_ids_description = _("Filter by tag ids...")

    inventory_subquery = Subquery(
        ProductInventory.objects.filter(product=OuterRef('id'))
                                .values("sale_price", "site_price", "increase_per")
                                .annotate(
                                    inventory_info=JSONObject(
                                        site_price=F("site_price"),
                                        sale_price=F("sale_price"),
                                        increase_per=F("increase_per")
                                    )
                                ).values("inventory_info")[:1]
    )
    image_subquery = Subquery(
        ProductImage.objects.filter(product=OuterRef("id"))
                            .values("image", "url")
                            .annotate(
                                image_info=JSONObject(
                                    image=F("image"),
                                    url=F("url")
                                )
                            ).values("image_info")[:1]
    )

    def get_query_filters(self, request):
        filters = {}
        category_id = request.query_params.get(self.category_param)
        if category_id:
            filters["categories__id"] = category_id

        product_ids = request.query_params.get(self.product_ids_param)
        if product_ids:
            filters["product_ids__in"] = [product_id for product_id in product_ids.split() if product_id.strip()]

        tag_ids = request.query_params.get(self.tag_ids_param)
        if tag_ids:
            filters["tags__id__in"] = [tag_id for tag_id in tag_ids.split() if tag_id.strip()]
        return filters

    def filter_queryset(self, request, queryset, view):
        if request.method == 'GET' and view.lookup_url_kwarg in view.kwargs:
            return (
                queryset.only('id', 'name', 'description', 'avg_rating', 'reviews_count', 'can_choose_tags', "images",
                              "inventories").prefetch_related("images", "inventories")
            )
        filters = self.get_query_filters(request)
        if filters:
            queryset = queryset.filter(**filters)
        return (
            queryset.values("id", "name", "avg_rating", "reviews_count")
                    .annotate(inventory_info=self.inventory_subquery, image_info=self.image_subquery)
        )

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.category_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.category_description),
                'schema': {
                    'type': 'string'
                }
            },
            {
                'name': self.product_ids_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.product_ids_description),
                'schema': {
                    'type': 'string'
                }
            },
            {
                'name': self.tag_ids_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.tag_ids_description),
                'schema': {
                    'type': 'string'
                }
            }
        ]


class BaseSQLProductsFilter(BaseFilterBackend):
    sql = None

    def filter_queryset(self, request, queryset, view):
        assert self.sql
        filters = self.get_filters(request)
        site = filters['site']
        limit, offset = filters['limit'], filters['offset']
        with connection.cursor() as cursor:
            cursor.execute(self.sql, [site + "%", limit, offset])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_filters(request):
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
        return {'site': site, 'limit': limit, 'offset': limit * page if page > 1 else 0}

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'site',
                'required': False,
                'in': 'query',
                'description': '',
                'schema': {
                    'type': 'string',
                    'default': 'rakuten'
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


class ProductSQLSearchFilter(BaseSQLProductsFilter):
    sql = """
    SELECT 
        p.id, 
        p.name, 
        p.avg_rating, 
        p.reviews_count, 
        (SELECT JSONB_BUILD_OBJECT(
            ('site_price')::text, inv.site_price, 
            ('sale_price')::text, inv.sale_price, 
            ('increase_per')::text, inv.increase_per) AS inventory_info
            FROM products_productinventory as inv WHERE inv.product_id = (p.id) LIMIT 1
        ) AS inventory_info,
        (SELECT JSONB_BUILD_OBJECT(
            ('image')::text, img.image, 
            ('url')::text, img.url) AS image_info 
            FROM products_productimage as img WHERE img.product_id = (p.id) LIMIT 1
        ) AS image_info 
    FROM products_product as p
    WHERE p.id LIKE %s AND p.is_active AND p.name ILIKE %s
    LIMIT %s OFFSET %s;
    """

    def filter_queryset(self, request, queryset, view):
        search_term = request.query_params.get('search')
        if not search_term:
            raise ValidationError({'detail': "search is required!"})

        filters = self.get_filters(request)
        site = filters['site']
        if search_term:
            limit, offset = filters['limit'], filters['offset']
            with connection.cursor() as cursor:
                cursor.execute(self.sql, [site + "%", f"%{search_term}%", limit, offset])
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
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
            }, *super().get_schema_operation_parameters(view)
        ]


class ProductSQLNewFilter(BaseSQLProductsFilter):
    sql = """
    SELECT DISTINCT ON (p.id) p.id,
        p.name,
        p.avg_rating,
        p.reviews_count,
        JSONB_BUILD_OBJECT(
            ('site_price')::text, inv.site_price,
            ('sale_price')::text, inv.sale_price,
            ('increase_per')::text, inv.increase_per
        ) AS inventory_info,
        JSONB_BUILD_OBJECT(
            ('image')::text, img.image,
            ('url')::text, img.url
        ) AS image_info
    FROM 
        products_product AS p
    JOIN 
        products_productinventory AS inv ON p.id = inv.product_id
    JOIN 
        products_productimage AS img ON p.id = img.product_id
    WHERE 
        p.id LIKE %s AND p.is_active
    ORDER BY 
        p.id, 
        p.created_at DESC
    LIMIT %s OFFSET %s;
    """


class ProductSQLPopularFilter(BaseSQLProductsFilter):
    sql = """
    SELECT DISTINCT ON (p.id) p.id,
        p.name,
        p.avg_rating,
        p.reviews_count,
        JSONB_BUILD_OBJECT(
            ('site_price')::text, inv.site_price,
            ('sale_price')::text, inv.sale_price,
            ('increase_per')::text, inv.increase_per
        ) AS inventory_info,
        JSONB_BUILD_OBJECT(
            ('image')::text, img.image,
            ('url')::text, img.url
        ) AS image_info
    FROM 
        products_product AS p
    JOIN 
        products_productinventory AS inv ON p.id = inv.product_id
    JOIN 
        products_productimage AS img ON p.id = img.product_id
    WHERE 
        p.id LIKE %s AND p.is_active AND p.site_avg_rating > 3.5 AND p.site_reviews_count > 1
    ORDER BY 
        p.id DESC, 
        p.site_avg_rating desc
    LIMIT %s OFFSET %s;
    """
