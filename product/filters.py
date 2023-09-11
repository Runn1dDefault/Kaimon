from django.contrib.admin import SimpleListFilter
from django.db.models import Avg, Q, F, Sum, Count, Case, When, Value, IntegerField
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import SearchFilter, BaseFilterBackend
from rest_framework.generics import get_object_or_404

from utils.mixins import LanguageMixin

from .querysets import ProductQuerySet


class FilterByTag(BaseFilterBackend):
    param = 'tag_ids'
    description = _('Filter by tag ids')

    def filter_queryset(self, request, queryset, view):
        tag_ids = request.query_params.get(self.param, '').split(',')
        if tag_ids:
            return queryset.filter(tags__id__in=tag_ids)
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
                },
            },
        ]


class ProductReferenceFilter(BaseFilterBackend):
    min_filter_qty = 1
    reference_qty = 10
    exclude_genre_levels = [0, 1]
    product_id_param = 'product_id'
    product_id_description = _('Recommendations by product meta')

    @staticmethod
    def filter_by_purchases_count(queryset, min_count: int = 0) -> ProductQuerySet:
        return queryset.annotate(
            purchases_count=Sum('receipts__purchases_count', output_field=IntegerField())
        ).filter(purchases_count__gt=min_count)

    @staticmethod
    def filter_by_reviews_count(queryset, min_count: int = 0) -> ProductQuerySet:
        return queryset.annotate(reviews_count=Count('reviews__id')).filter(reviews_count__gt=min_count)

    def filter_queryset(self, request, queryset, view):
        product_id = request.query_params.get(self.product_id_param)
        if product_id:
            # recommendations by product instance genres and tags
            product = get_object_or_404(queryset, id=product_id)
            genre_ids = product.genres.exclude(level__in=self.exclude_genre_levels).values_list('id', flat=True)
            tag_ids = product.tags.values_list('id', flat=True)
            return queryset.exclude(id=product_id).filter(Q(genres__id__in=genre_ids) | Q(tags__id__in=tag_ids))
        # recommendations by products purchases and reviews
        by_purchases_filtered = self.filter_by_purchases_count(queryset, min_count=self.min_filter_qty)
        by_reviews_filtered = self.filter_by_reviews_count(queryset, min_count=self.min_filter_qty)
        purchases_product_ids = list(by_purchases_filtered.values_list('id', flat=True))
        reviewed_product_ids = list(by_reviews_filtered.values_list('id', flat=True))
        reference_product_ids = purchases_product_ids + reviewed_product_ids
        return queryset.annotate(
            in_reference=Case(
                When(id__in=reference_product_ids, then=Value(True)),
                When(~Q(id__in=reference_product_ids), then=Value(False))
            )
        ).order_by('in_reference', F('reference_rank').desc(nulls_last=True))

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.product_id_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.product_id_description),
                'schema': {
                    'type': 'string',
                },
            },
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
