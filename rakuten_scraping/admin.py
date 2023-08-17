from django.contrib import admin

from rakuten_scraping.models import Oauth2Client


@admin.action(description="Disable")
def make_disable(modeladmin, request, queryset):
    queryset.update(disabled=True)


@admin.action(description="Active")
def make_active(modeladmin, request, queryset):
    queryset.update(disabled=False)


@admin.action(description="Set Free")
def set_free(modeladmin, request, queryset):
    queryset.update(disabled=False)
    for cli in queryset:
        cli.set_free()


@admin.register(Oauth2Client)
class OauthClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'app_id', 'disabled')
    list_filter = ('disabled',)
    search_fields = ('id', 'app_id',)
    actions = [make_disable, make_active, set_free]


