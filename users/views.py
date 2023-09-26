from rest_framework import generics, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .authentication import RestoreJWTAuthentication
from .serializers import RegistrationSerializer, UpdatePasswordSerializer, UserProfileSerializer, \
    ConfirmEmailSerializer, BaseRecoverySerializer, RecoveryCodeSerializer, RecoveryTokenSerializer


class RegistrationView(generics.CreateAPIView):
    permission_classes = ()
    authentication_classes = ()
    serializer_class = RegistrationSerializer


class BaseRecoveryView(generics.GenericAPIView):
    permission_classes = ()
    authentication_classes = ()

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        assert issubclass(serializer_class, BaseRecoverySerializer)
        return serializer_class

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecoveryCodeView(BaseRecoveryView):
    serializer_class = RecoveryCodeSerializer


class RecoveryTokenView(BaseRecoveryView):
    serializer_class = RecoveryTokenSerializer


class RecoveryPasswordView(mixins.UpdateModelMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (RestoreJWTAuthentication,)
    serializer_class = UpdatePasswordSerializer

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class ConfirmEmailView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ConfirmEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserInfoView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer

    def get_request_user(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        user = self.get_request_user()
        serializer = self.get_serializer(instance=user)
        return Response(serializer.data)


class UpdateUserInfo(generics.UpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user
