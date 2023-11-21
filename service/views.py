from rest_framework.generics import ListAPIView

from .models import Conversion
from .serializers import ConversionSerializer


class ConversionListView(ListAPIView):
    authentication_classes = ()
    permission_classes = ()
    queryset = Conversion.objects.all()
    serializer_class = ConversionSerializer
