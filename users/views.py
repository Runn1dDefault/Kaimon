from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from utils.views import PostAPIView
from .authentication import RestoreJWTAuthentication
from .serializers import RegistrationSerializer, RestoreSerializer, UpdatePasswordSerializer, UserProfileSerializer


class RegistrationView(PostAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RegistrationSerializer


class RestorePasswordView(PostAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RestoreSerializer


class UpdatePasswordView(PostAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (RestoreJWTAuthentication,)
    serializer_class = UpdatePasswordSerializer


class UserInfoView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer

    def get(self, request):
        serializer = self.get_serializer(instance=request.user, many=False)
        return Response(serializer.data)


class UpdateUserInfo(generics.UpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer
    lookup_field = None

    def get_object(self):
        return self.request.user
