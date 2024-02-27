def delete_products(products_query, products_count: int = None, delete_limit: int = 20_000):
    products = products_query
    count = products_count or products.count()

    remaining_count = count
    while remaining_count > 0:
        delete_count = min(remaining_count, delete_limit)
        products[:delete_count].delete()
        remaining_count -= delete_count
