from rest_framework.pagination import PageNumberPagination


class GenrePagination(PageNumberPagination):
    page_size = 40
    max_page_size = 40
    page_size_query_param = 'page_size'
