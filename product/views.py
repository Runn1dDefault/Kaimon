from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response

from currencies.mixins import CurrencyMixin
from users.permissions import RegistrationPayedPermission
from utils.mixins import LanguageMixin
from utils.schemas import LANGUAGE_QUERY_SCHEMA_PARAM, CURRENCY_QUERY_SCHEMA_PARAM
from utils.paginators import PagePagination

from .filters import SearchFilterByLang, GenreLevelFilter, PopularProductOrdering, ProductReferenceFilter, FilterByTag
from .models import Genre, Product, TagGroup
from .paginators import GenrePagination
from .serializers import ProductListSerializer, GenreSerializer, ProductReviewSerializer, ProductRetrieveSerializer, \
    TagByGroupSerializer
from .utils import get_genre_parents_tree


@api_view(['GET'])
def get_languages_view(request):
    return Response(settings.VERBOSE_LANGUAGES, status=status.HTTP_200_OK)


# -------------------------------------------------- Genres ------------------------------------------------------------
@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(name='level', type=OpenApiTypes.INT, required=False, default=1),
            LANGUAGE_QUERY_SCHEMA_PARAM
        ]
    )
)
class GenreListView(LanguageMixin, generics.ListAPIView):
    queryset = Genre.objects.filter(deactivated=False)
    filter_backends = [GenreLevelFilter]
    pagination_class = GenrePagination
    serializer_class = GenreSerializer


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class GenreChildrenView(LanguageMixin, generics.ListAPIView):
    lookup_field = 'id'
    queryset = Genre.objects.filter(deactivated=False)
    serializer_class = GenreSerializer
    pagination_class = None

    def list(self, request, *args, **kwargs):
        children = self.filter_queryset(self.get_object().children.filter(deactivated=False))
        page = self.paginate_queryset(children)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class GenreParentsView(LanguageMixin, generics.ListAPIView):
    lookup_field = 'id'
    queryset = Genre.objects.filter(deactivated=False)
    serializer_class = GenreSerializer

    def list(self, request, *args, **kwargs):
        parents_queryset = self.get_queryset().exclude(level=0).filter(id__in=get_genre_parents_tree(self.get_object()))
        parents = self.filter_queryset(parents_queryset)
        page = self.paginate_queryset(parents)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(parents, many=True)
        return Response(serializer.data)


# ------------------------------------------------ Products ------------------------------------------------------------
@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM, CURRENCY_QUERY_SCHEMA_PARAM]))
class ProductsListByGenreView(CurrencyMixin, LanguageMixin, generics.ListAPIView):
    lookup_field = 'genres__id'
    lookup_url_kwarg = 'id'
    queryset = Product.objects.filter(is_active=True, availability=True)
    filter_backends = [PopularProductOrdering, filters.OrderingFilter, FilterByTag]
    pagination_class = PagePagination
    serializer_class = ProductListSerializer
    ordering_fields = ['created_at', 'price']


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class TagByGenreListView(LanguageMixin, generics.ListAPIView):
    lookup_field = 'tags__product_set__genres__id'
    lookup_url_kwarg = 'id'
    queryset = TagGroup.objects.groups_with_tags()
    serializer_class = TagByGroupSerializer
    pagination_class = None


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM, CURRENCY_QUERY_SCHEMA_PARAM]))
class ProductRetrieveView(CurrencyMixin, LanguageMixin, generics.RetrieveAPIView):
    lookup_field = 'id'
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductRetrieveSerializer


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM, CURRENCY_QUERY_SCHEMA_PARAM]))
class SearchProductView(CurrencyMixin, LanguageMixin, generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True, availability=True)
    pagination_class = PagePagination
    serializer_class = ProductListSerializer
    filter_backends = [SearchFilterByLang]
    search_fields_ja = ['name', 'genres__name', 'tags__name']
    search_fields_ru = ['name_ru', 'genres__name_ru', 'tags__name_ru']
    search_fields_en = ['name_en', 'genres__name_en', 'tags__name_en']
    search_fields_tr = ['name_tr', 'genres__name_tr', 'tags__name_tr']
    search_fields_ky = ['name_ky', 'genres__name_ky', 'tags__name_ky']
    search_fields_kz = ['name_kz', 'genres__name_kz', 'tags__name_kz']


# ------------------------------------------------- Reviews ------------------------------------------------------------
class ProductReviewCreateView(generics.CreateAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [RegistrationPayedPermission]


class ProductReviewListView(generics.ListAPIView):
    lookup_field = 'id'
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductReviewSerializer
    pagination_class = PagePagination

    def list(self, request, *args, **kwargs):
        product = self.get_object()
        queryset = self.filter_queryset(product.reviews.filter(is_active=True))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# -------------------------------------------- Recommendations ---------------------------------------------------------
@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM, CURRENCY_QUERY_SCHEMA_PARAM]))
class ReferenceListView(CurrencyMixin, LanguageMixin, generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True, availability=True)
    filter_backends = [ProductReferenceFilter]
    serializer_class = ProductListSerializer
    pagination_class = PagePagination
