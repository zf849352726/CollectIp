from django.contrib import admin

from .models import BackgroundJob, OperationLog, Proxy, ProxyCheckHistory, SystemSettings


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
        "collection_successes",
        "collection_failures",
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


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "level", "module", "event", "proxy_server", "job")
    list_filter = ("level", "module", "event")
    search_fields = ("message", "proxy_server")
    readonly_fields = (
        "created_at",
        "level",
        "module",
        "event",
        "message",
        "details",
        "proxy_server",
        "job",
    )
