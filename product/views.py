from django.conf import settings
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .filters import SearchFilterByLang, GenreProductsFilter, GenreLevelFilter
from .mixins import LanguageMixin
from .models import Genre, Product
from .paginators import PagePagination, GenrePagination
from .serializers import ProductSerializer, GenreSerializer


@api_view(['GET'])
def get_languages_view(request):
    return Response(settings.VERBOSE_LANGUAGES, status=status.HTTP_200_OK)


class GenreView(viewsets.ReadOnlyModelViewSet, LanguageMixin):
    queryset = Genre.objects.filter(Q(deactivated__isnull=True) | Q(deactivated=False))
    filter_backends = [GenreLevelFilter]
    pagination_class = GenrePagination
    serializer_class = GenreSerializer
    query_schema = [
        OpenApiParameter(name='level', type=OpenApiTypes.INT, required=False, default=1),
        OpenApiParameter(name=settings.LANGUAGE_QUERY, type=OpenApiTypes.STR, required=False, default='ja'),
    ]

    @extend_schema(parameters=query_schema)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(parameters=query_schema)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(name=settings.LANGUAGE_QUERY, type=OpenApiTypes.STR, required=False, default='ja'),
        ]
    )
)
class GenreProductsListView(generics.ListAPIView, LanguageMixin):
    lookup_field = 'id'
    queryset = Genre.objects.filter(Q(deactivated__isnull=True) | Q(deactivated=False))
    filter_backends = [GenreProductsFilter]
    pagination_class = PagePagination
    serializer_class = ProductSerializer


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(name=settings.LANGUAGE_QUERY, type=OpenApiTypes.STR, required=False, default='ja'),
        ]
    )
)
class SearchProduct(generics.ListAPIView, LanguageMixin):
    queryset = Product.objects.filter(is_active=True)
    pagination_class = PagePagination
    serializer_class = ProductSerializer
    filter_backends = [SearchFilterByLang]
    search_fields_ja = ['name', 'genres__name', 'brand_name']
    search_fields_ru = ['name_ru', 'genres__name_ru', 'brand_name_ru']
    search_fields_en = ['name_en', 'genres__name_en', 'brand_name_en']
    search_fields_tr = ['name_tr', 'genres__name_tr', 'brand_name_tr']
    search_fields_ky = ['name_ky', 'genres__name_ky', 'brand_name_ky']
    search_fields_kz = ['name_kz', 'genres__name_kz', 'brand_name_kz']
