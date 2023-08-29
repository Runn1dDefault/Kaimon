from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import generics, permissions, mixins, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from product.models import Product, ProductReview
from product.serializers import ProductSerializer, ProductReviewSerializer
from utils.filters import FilterByFields
from utils.mixins import LanguageMixin
from utils.paginators import PagePagination
from utils.schemas import LANGUAGE_QUERY_SCHEMA_PARAM


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_QUERY_SCHEMA_PARAM]))
class AdminProductListView(LanguageMixin, generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = ProductSerializer
    pagination_class = PagePagination


class AdminReviewView(mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = ProductReview.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [FilterByFields]
    serializer_class = ProductReviewSerializer
    pagination_class = PagePagination
    lookup_field = 'id'
    filter_fields = {'is_read': {'db_field': 'is_read', 'type': 'boolean'}}

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def get_new_reviews_count(request):
    return Response({'count': ProductReview.objects.filter(is_active=True, is_read=False).count()})
