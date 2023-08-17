from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from utils.transforms import concat_to_upper_string
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('id', 'email', 'role', 'is_active', 'registration_payed', 'date_joined')
    list_filter = ('role', 'registration_payed', 'date_joined', 'last_login',
                   "is_staff", "is_superuser", "is_active", "groups")
    search_fields = ('id', 'email', 'full_name', 'username')
    search_help_text = _('Search by fields: ' + concat_to_upper_string(search_fields))
    ordering = ("date_joined",)
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
                "prepopulated_fields": {'username': ('email',)}
            },
        ),
    )
    fieldsets = (
        (_("Credentials"), {"fields": ("email", "username", "password")}),
        (_("Personal info"), {"fields": ("full_name", "image",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "role",
                    "registration_payed",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
