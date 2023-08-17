from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegistrationView, RestorePasswordView, UpdatePasswordView, UserInfoView


urlpatterns = [
    path('registration/', RegistrationView.as_view(), name='auth_registration'),
    path('token/', TokenObtainPairView.as_view(), name='auth_token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('restore/password/', RestorePasswordView.as_view(), name='auth_restore_pwd'),
    path('update/password/', UpdatePasswordView.as_view(), name='auth_update_pwd'),
    path('me-info/', UserInfoView.as_view(), name='auth_me_info')
]
