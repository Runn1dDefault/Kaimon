from rest_framework import generics, permissions

from users.permissions import IsDirectorPermission


from currency_conversion.models import Conversion
from .serializers import AdminConversionSerializer


class AdminConversionListView(generics.ListAPIView):
    queryset = Conversion.objects.all().order_by('-id')
    permission_classes = [permissions.IsAuthenticated, IsDirectorPermission]
    serializer_class = AdminConversionSerializer


class AdminUpdateConversionView(generics.UpdateAPIView):
    lookup_field = 'id'
    queryset = Conversion.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsDirectorPermission]
    serializer_class = AdminConversionSerializer
