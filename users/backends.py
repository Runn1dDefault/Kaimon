from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import User


class EmailOrUsernameAuthBackend(ModelBackend):
    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and getattr(user, "registration_payed", True)

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = User.objects.filter(Q(email=username) | Q(username=username)).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
