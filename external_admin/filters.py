from django.db import connection
from rest_framework.exceptions import ValidationError

from products.filters import BaseSQLProductsFilter
from service.utils import get_tuple_from_query_param


class ProductAdminSQLFilter(BaseSQLProductsFilter):
    sql = '''
    SELECT 
        p.id,
        p.name, 
        p.avg_rating, 
        p.reviews_count, 
        p.is_active,
        (
            SELECT 
                JSONB_BUILD_OBJECT(
                    ('site_price')::text, inv.site_price, 
                    ('sale_price')::text, inv.sale_price, 
                    ('increase_per')::text, inv.increase_per
                ) AS inventory_info
            FROM products_productinventory AS inv 
            WHERE inv.product_id = (p.id) LIMIT 1
        ) AS inventory_info,
        (
            SELECT 
                JSONB_BUILD_OBJECT(
                    ('image')::text, img.image, 
                    ('url')::text, img.url
                ) AS image_info 
            FROM products_productimage AS img 
            WHERE img.product_id = (p.id) LIMIT 1
        ) AS image_info 
    FROM 
        products_product as p
    WHERE p.id LIKE %s 
    ORDER BY p.id
    LIMIT %s OFFSET %s;
    '''

    def get_sql(self, request) -> tuple[str, list]:
        filters = self.get_filters(request)
        site, limit, offset = filters['site'], filters['limit'], filters['offset']
        return self.sql, [site + '%', limit, offset]

    def filter_queryset(self, request, queryset, view):
        with connection.cursor() as cursor:
            sql, params = self.get_sql(request)
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


class SearchProductAdminSQLFilter(ProductAdminSQLFilter):
    sql_by_ids = '''
    SELECT 
        p.id,
        p.name, 
        p.avg_rating, 
        p.reviews_count, 
        p.is_active,
        (
            SELECT 
                JSONB_BUILD_OBJECT(
                    ('site_price')::text, inv.site_price, 
                    ('sale_price')::text, inv.sale_price, 
                    ('increase_per')::text, inv.increase_per
                ) AS inventory_info
            FROM products_productinventory AS inv 
            WHERE inv.product_id = (p.id) LIMIT 1
        ) AS inventory_info,
        (
            SELECT 
                JSONB_BUILD_OBJECT(
                    ('image')::text, img.image, 
                    ('url')::text, img.url
                ) AS image_info 
            FROM products_productimage AS img 
            WHERE img.product_id = (p.id) LIMIT 1
        ) AS image_info 
    FROM 
        products_product as p
    WHERE p.ids IN %s
    ORDER BY p.id
    LIMIT %s OFFSET %s;
    '''
    sql = '''
    SELECT 
        p.id,
        p.name, 
        p.avg_rating, 
        p.reviews_count, 
        p.is_active,
        (
            SELECT 
                JSONB_BUILD_OBJECT(
                    ('site_price')::text, inv.site_price, 
                    ('sale_price')::text, inv.sale_price, 
                    ('increase_per')::text, inv.increase_per
                ) AS inventory_info
            FROM products_productinventory AS inv 
            WHERE inv.product_id = (p.id) LIMIT 1
        ) AS inventory_info,
        (
            SELECT 
                JSONB_BUILD_OBJECT(
                    ('image')::text, img.image, 
                    ('url')::text, img.url
                ) AS image_info 
            FROM products_productimage AS img 
            WHERE img.product_id = (p.id) LIMIT 1
        ) AS image_info 
    FROM 
        products_product as p
    WHERE p.id LIKE %s AND p.name ILIKE %s
    ORDER BY p.id
    LIMIT %s OFFSET %s;
    '''

    def get_sql(self, request) -> list:
        search_type = request.query_params.get("search_type", "name")

        search_term = request.query_params.get("search")
        if not search_term:
            raise ValidationError({'detail': 'search is required!'})

        filters = self.get_filters(request)
        site, limit, offset = filters['site'], filters['limit'], filters['offset']

        match search_type:
            case "name":
                sql = self.sql
                params = [site + '%', f"%{search_term}%",  limit, offset]
            case "ids":
                sql = self.sql_by_ids
                ids = get_tuple_from_query_param(search_term)
                params = [ids, limit, offset]
            case _:
                raise ValidationError({'detail': 'unsupported search type!'})
        return sql, params
