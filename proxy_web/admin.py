from django.contrib import admin

from .models import BackgroundJob, Proxy, ProxyCheckHistory, SystemSettings


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = (
        "server",
        "country",
        "proxy_type",
        "score",
        "is_available",
        "latency_ms",
        "success_rate",
        "last_checked_at",
    )
    list_filter = ("is_available", "is_archived", "country", "proxy_type")
    search_fields = ("server", "country")


@admin.register(ProxyCheckHistory)
class ProxyCheckHistoryAdmin(admin.ModelAdmin):
    list_display = ("proxy", "available", "latency_ms", "exit_ip", "test_url", "checked_at")
    list_filter = ("available", "protocol", "error_type")


admin.site.register(SystemSettings)
admin.site.register(BackgroundJob)
