from django.core.paginator import InvalidPage, Page
from django.db.models import QuerySet
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination


class GenrePagination(PageNumberPagination):
    page_size = 40
    max_page_size = 40
    page_size_query_param = 'page_size'


class QuerysetPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 30
    page_size_query_param = 'page_size'

    def paginate_queryset(self, queryset, request, view=None) -> QuerySet | None:
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = self.get_page_number(request, paginator)
        number = paginator.validate_number(page_number)
        bottom = (number - 1) * paginator.per_page
        top = bottom + paginator.per_page
        if top + paginator.orphans >= paginator.count:
            top = paginator.count

        sliced_queryset = queryset[bottom:top]
        try:
            self.page = Page(sliced_queryset, number, paginator)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=str(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True
        self.request = request
        return queryset.filter(id__in=sliced_queryset.values_list('id', flat=True))
