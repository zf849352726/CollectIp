from django.db import models
from django.db.models import Q


class Proxy(models.Model):
    server = models.CharField(max_length=64, unique=True, verbose_name="代理地址")
    ping = models.FloatField(null=True, blank=True, verbose_name="源站延迟")
    speed = models.FloatField(null=True, blank=True, verbose_name="源站速度")
    uptime1 = models.CharField(max_length=16, default="N/A")
    uptime2 = models.CharField(max_length=16, default="N/A")
    proxy_type = models.CharField(max_length=32, default="Unknown")
    country = models.CharField(max_length=64, default="Unknown")
    ssl = models.CharField(max_length=128, default="N/A")
    conn = models.CharField(max_length=128, default="N/A")
    post = models.CharField(max_length=128, default="N/A")
    source_last_work_time = models.CharField(max_length=64, default="N/A")
    source = models.CharField(max_length=64, default="freeproxylist.org", db_index=True)

    score = models.PositiveSmallIntegerField(default=50, db_index=True)
    is_available = models.BooleanField(default=False, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    success_rate = models.FloatField(default=0)
    consecutive_failures = models.PositiveIntegerField(default=0)
    last_checked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_success_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now_add=True, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["is_archived", "-is_available", "-score", "latency_ms", "server"]

    def __str__(self) -> str:
        return self.server


class ProxyCheckHistory(models.Model):
    proxy = models.ForeignKey(Proxy, on_delete=models.CASCADE, related_name="checks")
    available = models.BooleanField(db_index=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    checked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    error_type = models.CharField(max_length=64, blank=True, default="")
    error_message = models.CharField(max_length=255, blank=True, default="")
    exit_ip = models.GenericIPAddressField(null=True, blank=True)
    test_url = models.URLField(max_length=500)
    protocol = models.CharField(max_length=8)

    class Meta:
        ordering = ["-checked_at"]
        indexes = [
            models.Index(
                fields=["proxy", "-checked_at"],
                name="proxy_web_p_proxy_i_128cc4_idx",
            )
        ]


class SystemSettings(models.Model):
    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    auto_collect = models.BooleanField(default=False)
    auto_score = models.BooleanField(default=True)
    collection_interval = models.PositiveIntegerField(default=3600)
    score_interval = models.PositiveIntegerField(default=300)
    max_pages = models.PositiveSmallIntegerField(default=5)
    captcha_retries = models.PositiveSmallIntegerField(default=8)
    check_timeout = models.PositiveSmallIntegerField(default=8)
    check_workers = models.PositiveSmallIntegerField(default=20)
    archive_after_failures = models.PositiveSmallIntegerField(default=10)
    purge_after_days = models.PositiveSmallIntegerField(default=30)
    last_collection_at = models.DateTimeField(null=True, blank=True)
    last_score_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def load(cls):
        instance, _ = cls.objects.get_or_create(singleton_key=1)
        return instance


class BackgroundJob(models.Model):
    KIND_CHOICES = [("collect", "采集"), ("score", "评分"), ("cleanup", "清理")]
    STATUS_CHOICES = [
        ("queued", "排队"),
        ("running", "运行中"),
        ("success", "成功"),
        ("failed", "失败"),
    ]

    kind = models.CharField(max_length=16, choices=KIND_CHOICES, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="queued", db_index=True)
    active_key = models.CharField(max_length=16, unique=True, null=True, blank=True)
    message = models.TextField(blank=True, default="")
    progress = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["queued", "running", "success", "failed"]),
                name="valid_background_job_status",
            )
        ]
