from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from users.permissions import RegistrationPayedPermission
from utils.mixins import LanguageMixin
from utils.schemas import LANGUAGE_QUERY_SCHEMA_PARAM

from .filters import SearchFilterByLang, GenreProductsFilter, GenreLevelFilter
from .models import Genre, Product
from .paginators import PagePagination, GenrePagination
from .serializers import ProductSerializer, GenreSerializer, ProductReviewSerializer


@api_view(['GET'])
def get_languages_view(request):
    return Response(settings.VERBOSE_LANGUAGES, status=status.HTTP_200_OK)


class GenreReadViewSet(LanguageMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Genre.objects.filter(Q(deactivated__isnull=True) | Q(deactivated=False))
    filter_backends = [GenreLevelFilter]
    pagination_class = GenrePagination
    serializer_class = GenreSerializer

    @extend_schema(
        parameters=[OpenApiParameter(name='level', type=OpenApiTypes.INT, required=False, default=1),
                    LANGUAGE_QUERY_SCHEMA_PARAM]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        parameters=[OpenApiParameter(name='level', type=OpenApiTypes.INT, required=False, default=1),
                    LANGUAGE_QUERY_SCHEMA_PARAM]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class GenreProductsListView(LanguageMixin, generics.ListAPIView):
    lookup_field = 'id'
    queryset = Genre.objects.filter(Q(deactivated__isnull=True) | Q(deactivated=False))
    filter_backends = [GenreProductsFilter]
    pagination_class = PagePagination
    serializer_class = ProductSerializer


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class SearchProductView(LanguageMixin, generics.ListAPIView):
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


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class NewProductsView(LanguageMixin, generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    pagination_class = PagePagination

    def get_queryset(self):
        ten_days_ago = (timezone.now() - timezone.timedelta(days=10)).date()
        return super().get_queryset().filter(Q(created_at__date__gte=ten_days_ago) | Q(release_date__gte=ten_days_ago))


class ProductReviewView(generics.ListCreateAPIView):
    lookup_field = 'id'
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductReviewSerializer
    permission_classes = [RegistrationPayedPermission]
    pagination_class = PagePagination

    def create(self, request, *args, **kwargs):
        product = self.get_object()
        data = {'product': product.id, **request.data}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        product = self.get_object()
        queryset = self.filter_queryset(product.reviews.filter(is_active=True))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class PopularProductsView(generics.ListAPIView, LanguageMixin):
    queryset = Product.objects.filter(is_active=True).popular_by_orders_qty()
    serializer_class = ProductSerializer
    pagination_class = PagePagination
