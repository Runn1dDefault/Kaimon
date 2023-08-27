from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter


LANGUAGE_QUERY_SCHEMA_PARAM = OpenApiParameter(
    name=settings.LANGUAGE_QUERY,
    type=OpenApiTypes.STR,
    required=False,
    default='ja'
)
