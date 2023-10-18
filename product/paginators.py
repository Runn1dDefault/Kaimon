from django.core.paginator import InvalidPage
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination


class GenrePagination(PageNumberPagination):
    page_size = 40
    max_page_size = 40
    page_size_query_param = 'page_size'


class QuerySetPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 30
    page_size_query_param = 'page_size'

    def __init__(self):
        self.page = None
        self.request = None

    def paginate_queryset(self, queryset, request, view=None):
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = self.get_page_number(request, paginator)

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=str(exc)
            )
            raise NotFound(msg)
        else:
            if paginator.num_pages > 1 and self.template is not None:
                # The browsable API should display pagination controls.
                self.display_page_controls = True

            self.request = request
            return self.page.object_list
