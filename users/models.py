from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.utils.translation import gettext_lazy as _

from users.validators import validate_full_name


class UserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields['registration_payed'] = False
        extra_fields['is_active'] = False
        return super().create_user(username, email=email, password=password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields['registration_payed'] = True
        extra_fields['is_active'] = True
        extra_fields['role'] = User.Role.MANAGER
        return super().create_superuser(username, email=email, password=password, **extra_fields)


class User(AbstractUser):
    objects = UserManager()

    class Role(models.TextChoices):
        DIRECTOR = 'director', _('Director')
        MANAGER = 'manager', _('Manager')
        CLIENT = 'client', _('Client')

    full_name = models.CharField(max_length=300, validators=[validate_full_name])
    role = models.CharField(choices=Role.choices, max_length=10, default=Role.CLIENT)
    image = models.ImageField(upload_to='users/', blank=True, null=True)
    registration_payed = models.BooleanField(default=False)

    @property
    def is_director(self) -> bool:
        return self.role == self.Role.DIRECTOR

    @property
    def is_manager(self) -> bool:
        return self.role == self.Role.MANAGER

    @property
    def is_client(self) -> bool:
        return self.role == self.Role.CLIENT
