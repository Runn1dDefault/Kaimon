import logging

from products.models import Product


def delete_products(products_query, products_count: int = None, delete_limit: int = 20_000):
    products = products_query
    count = products_count or products.count()

    remaining_count = count
    while remaining_count > 0:
        delete_count = min(remaining_count, delete_limit)
        product_ids = products[:delete_count].values_list("id", flat=True)
        Product.objects.filter(id__in=product_ids).delete()
        logging.info("DELETED products %s" % delete_count)
        remaining_count -= delete_count
