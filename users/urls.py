from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegistrationView, RestorePasswordView, UpdatePasswordView, UserInfoView, UpdateUserInfo


urlpatterns = [
    path('auth/registration/', RegistrationView.as_view(), name='auth_registration'),
    path('auth/token/', TokenObtainPairView.as_view(), name='auth_token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('auth/restore/password/', RestorePasswordView.as_view(), name='auth_restore_pwd'),
    path('auth/update/password/', UpdatePasswordView.as_view(), name='auth_update_pwd'),
    path('auth/me-info/', UserInfoView.as_view(), name='auth_me_info'),
    path('auth/me-info/update/', UpdateUserInfo.as_view(), name='auth_me_info_update'),
    path('admin/', include('users.admin.urls'))
]

