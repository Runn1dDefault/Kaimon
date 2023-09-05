from django.contrib.admin import SimpleListFilter
from django.db.models import Avg, Q, Count
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import SearchFilter, BaseFilterBackend
from rest_framework.generics import get_object_or_404

from product.querysets import ProductQuerySet
from utils.mixins import LanguageMixin


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
            assert isinstance(queryset, ProductQuerySet)
            return queryset.order_by_popular()
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
                },
            },
        ]


class SearchFilterByLang(SearchFilter):
    def get_search_fields(self, view, request):
        assert isinstance(view, LanguageMixin)
        lang = view.get_lang()
        return getattr(view, f'search_fields_{lang}', None)


class GenreProductsFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_kwargs = {view.lookup_field: view.kwargs[view.lookup_url_kwarg or view.lookup_field]}
        genre = get_object_or_404(queryset, **filter_kwargs)
        view.check_object_permissions(request, genre)
        return genre.product_set.filter(is_active=True)


class GenreLevelFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        level = request.query_params.get('level', 1)
        filter_kwargs = dict(level=level)
        return queryset.filter(**filter_kwargs)


class ProductRankAdminFilter(SimpleListFilter):
    title = _('Rank')
    parameter_name = 'rank'

    def lookups(self, request, model_admin):
        return [
            ("Unranked", _("Unranked")),
            ("0.5", _("★☆☆☆☆")),
            ("1.0", _("⭐☆☆☆☆")),
            ("1.5", _("⭐★☆☆☆")),
            ("2.0", _("⭐⭐☆☆☆")),
            ("2.5", _("⭐⭐★☆☆")),
            ("3.0", _("⭐⭐⭐☆☆")),
            ("3.5", _("⭐⭐⭐★☆")),
            ("4.0", _("⭐⭐⭐⭐☆")),
            ("4.5", _("⭐⭐⭐⭐★")),
            ("5.0", _("⭐⭐⭐⭐⭐")),
        ]

    def queryset(self, request, queryset):
        base_queryset = queryset.annotate(avg_rank=Avg('reviews__rank', filter=Q(reviews__is_active=True)))
        value = self.value()
        match value:
            case "Unranked":
                return base_queryset.filter(avg_rank=0.0)
            case "0.5":
                return base_queryset.filter(avg_rank__gt=0, avg_rank__lte=0.5)
            case "1.0":
                return base_queryset.filter(avg_rank__gt=0.5, avg_rank__lte=1.0)
            case "1.5":
                return base_queryset.filter(avg_rank__gt=1.0, avg_rank__lte=1.5)
            case "2.0":
                return base_queryset.filter(avg_rank__gt=1.5, avg_rank__lte=2.0)
            case "2.5":
                return base_queryset.filter(avg_rank__gt=2.0, avg_rank__lte=2.5)
            case "3.0":
                return base_queryset.filter(avg_rank__gt=2.5, avg_rank__lte=3.0)
            case "3.5":
                return base_queryset.filter(avg_rank__gt=3.0, avg_rank__lte=3.5)
            case "4.0":
                return base_queryset.filter(avg_rank__gt=3.5, avg_rank__lte=4.0)
            case "4.5":
                return base_queryset.filter(avg_rank__gt=4.0, avg_rank__lte=4.5)
            case "5.0":
                return base_queryset.filter(avg_rank__gt=4.5)
            case _:
                return queryset
