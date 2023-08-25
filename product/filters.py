from rest_framework.filters import SearchFilter, BaseFilterBackend
from rest_framework.generics import get_object_or_404

from .mixins import LanguageMixin


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
