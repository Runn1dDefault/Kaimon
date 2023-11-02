from rest_framework.generics import ListAPIView

from external_admin.serializers import ConversionAdminSerializer
from users.permissions import EmailConfirmedPermission
from .models import Conversion


class ConversionListView(ListAPIView):
    permission_classes = (EmailConfirmedPermission,)
    queryset = Conversion.objects.all()
    serializer_class = ConversionAdminSerializer
