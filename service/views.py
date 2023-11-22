from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from .models import Conversion
from .serializers import ConversionSerializer


class ConversionListView(ListAPIView):
    permission_classes = (AllowAny,)
    queryset = Conversion.objects.all()
    serializer_class = ConversionSerializer
