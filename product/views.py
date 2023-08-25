from django.conf import settings
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .filters import SearchFilterByLang, GenreProductsFilter
from .mixins import LanguageMixin
from .models import Genre, Product
from .paginators import PagePagination
from .serializers import ProductSerializer
from .utils import get_request_lang


@api_view(['GET'])
def get_languages_view(request):
    return Response({'data': list(settings.SUPPORTED_LANG)}, status=status.HTTP_200_OK)


@api_view(['GET'])
def genres_info_view(request):
    genre_id = request.query_params.get('genre_id')
    lang = get_request_lang(request)
    base_queryset = Genre.objects.filter(deactivated=False)
    queryset = base_queryset.filter(level=1) if not genre_id else base_queryset.filter(id=genre_id)
    if not queryset.exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    field_name = 'name' if lang == 'ja' else f'name_{lang}'
    genres_data = queryset.genre_info_with_relations(name_field=field_name)
    return Response(genres_data, status=status.HTTP_200_OK)


class GenreProductsListView(generics.ListAPIView, LanguageMixin):
    lookup_field = 'id'
    lookup_url_kwarg = 'genre_id'
    queryset = Genre.objects.filter(Q(deactivated__isnull=True) | Q(deactivated=False))
    filter_backends = [GenreProductsFilter]
    pagination_class = PagePagination
    serializer_class = ProductSerializer


class SearchProduct(generics.ListAPIView, LanguageMixin):
    queryset = Product.objects.filter(is_active=True)
    pagination_class = PagePagination
    serializer_class = ProductSerializer
    filter_backends = [SearchFilterByLang]
    search_fields_ja = ['name', 'genre__name', 'brand_name']
    search_fields_ru = ['name_ru', 'genre__name_ru', 'brand_name_ru']
    search_fields_en = ['name_en', 'genre__name_en', 'brand_name_en']
    search_fields_tr = ['name_tr', 'genre__name_tr', 'brand_name_tr']
    search_fields_ky = ['name_ky', 'genre__name_ky', 'brand_name_ky']
    search_fields_kz = ['name_kz', 'genre__name_kz', 'brand_name_kz']
