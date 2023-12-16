from rest_framework.pagination import PageNumberPagination


class CategoryPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 50
    page_size_query_param = 'page_size'


class ProductPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 30
    page_size_query_param = 'page_size'


class ProductReviewPagination(PageNumberPagination):
    page_size = 5
    max_page_size = 20
    page_size_query_param = 'page_size'
