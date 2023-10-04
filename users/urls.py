from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegistrationView, UserInfoView, UpdateUserInfo, \
    ConfirmEmailView, RecoveryCodeView, RecoveryTokenView, RecoveryPasswordView

urlpatterns = [
    path('registration/', RegistrationView.as_view(), name='auth-registration'),
    path('token/', TokenObtainPairView.as_view(), name='auth-token-obtain-pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('confirm/email/', ConfirmEmailView.as_view(), name='auth-email-confirm'),
    path('me-info/', UserInfoView.as_view(), name='auth-me-info'),
    path('me-info/update/', UpdateUserInfo.as_view(), name='auth-me-info-update'),
    path('send-verification-code/', RecoveryCodeView.as_view(), name='auth-restore-mailing-code'),
    path('pwd-update-token/', RecoveryTokenView.as_view(), name='auth-restore-token'),
    path('recovery/password/', RecoveryPasswordView.as_view(), name='auth-update-pwd')
]
