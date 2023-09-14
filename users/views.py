from rest_framework import generics, status, mixins
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .authentication import RestoreJWTAuthentication
from .serializers import RegistrationSerializer, RestoreSerializer, UpdatePasswordSerializer, UserProfileSerializer


class RegistrationView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RegistrationSerializer


class RestorePasswordView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RestoreSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdatePasswordView(mixins.UpdateModelMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (RestoreJWTAuthentication,)
    serializer_class = UpdatePasswordSerializer

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class UserInfoView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class UpdateUserInfo(generics.UpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user
