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
    list_display_links = ('id', 'email',)
    search_fields = ('id', 'email', 'full_name', 'username')
    search_help_text = _('Search by fields: ' + concat_to_upper_string(search_fields))
    ordering = ("date_joined",)
    prepopulated_fields = {'username': ('email',)}
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email",  "full_name", "password1", "password2"),
            }
        ),
        (
            _("Advanced options"),
            {
                "classes": ("collapse",),
                "fields": ("role", "image", "registration_payed"),
            }
        )
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

    def has_add_permission(self, request):
        return request.user.is_superuser

    @staticmethod
    def check_to_obj_perm(user, obj):
        if not user.is_superuser and obj.is_superuser:
            return False
        if not user.is_superuser and obj.is_staff:
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and not self.check_to_obj_perm(user=request.user, obj=obj):
            return False
        return super().has_change_permission(request=request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        if obj and not self.check_to_obj_perm(user=request.user, obj=obj):
            return False
        return super().has_delete_permission(request=request, obj=obj)
