from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from users.models import User
from users.admin.paginators import UserListPagination

from .serializers import AdminUserSerializer


class UserAdminMixin:
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    pagination_class = UserListPagination
    queryset = User.objects.filter(role__in=[User.Role.CLIENT])
    serializer_class = AdminUserSerializer


class UserListView(UserAdminMixin, generics.ListAPIView):
    pass


class UserSearchView(UserAdminMixin, generics.ListAPIView):
    filter_backends = [SearchFilter]
    search_fields = ['email', 'full_name', 'id']


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def block_or_unblock_user_view(request, user_id):
    if request.user.role == User.Role.DIRECTOR:
        queryset = User.objects.exclude(role=User.Role.DEVELOPER)
    else:
        queryset = User.objects.filter(role=User.Role.CLIENT)
    user = get_object_or_404(queryset, id=user_id)
    user.is_active = not user.is_active
    user.save()
    return Response(status=status.HTTP_200_OK)
