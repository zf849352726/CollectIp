from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("proxy_web", "0001_initial")]
    operations = [
        migrations.AddField(model_name="proxy", name="source", field=models.CharField(db_index=True, default="freeproxylist.org", max_length=64)),
        migrations.AddField(model_name="proxy", name="is_archived", field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name="proxy", name="success_rate", field=models.FloatField(default=0)),
        migrations.AddField(model_name="proxy", name="last_success_at", field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name="proxy", name="last_seen_at", field=models.DateTimeField(auto_now_add=True, db_index=True, default=django.utils.timezone.now), preserve_default=False),
        migrations.AddField(model_name="proxy", name="archived_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AlterModelOptions(name="proxy", options={"ordering": ["is_archived", "-is_available", "-score", "latency_ms", "server"]}),
        migrations.CreateModel(
            name="SystemSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("singleton_key", models.PositiveSmallIntegerField(default=1, editable=False, unique=True)),
                ("auto_collect", models.BooleanField(default=False)),
                ("auto_score", models.BooleanField(default=True)),
                ("collection_interval", models.PositiveIntegerField(default=3600)),
                ("score_interval", models.PositiveIntegerField(default=300)),
                ("max_pages", models.PositiveSmallIntegerField(default=5)),
                ("captcha_retries", models.PositiveSmallIntegerField(default=8)),
                ("check_timeout", models.PositiveSmallIntegerField(default=8)),
                ("check_workers", models.PositiveSmallIntegerField(default=20)),
                ("archive_after_failures", models.PositiveSmallIntegerField(default=10)),
                ("purge_after_days", models.PositiveSmallIntegerField(default=30)),
                ("last_collection_at", models.DateTimeField(blank=True, null=True)),
                ("last_score_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="BackgroundJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("collect", "采集"), ("score", "评分"), ("cleanup", "清理")], db_index=True, max_length=16)),
                ("status", models.CharField(choices=[("queued", "排队"), ("running", "运行中"), ("success", "成功"), ("failed", "失败")], db_index=True, default="queued", max_length=16)),
                ("active_key", models.CharField(blank=True, max_length=16, null=True, unique=True)),
                ("message", models.TextField(blank=True, default="")),
                ("progress", models.PositiveIntegerField(default=0)),
                ("total", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(model_name="backgroundjob", constraint=models.CheckConstraint(condition=models.Q(("status__in", ["queued", "running", "success", "failed"])), name="valid_background_job_status")),
        migrations.CreateModel(
            name="ProxyCheckHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("available", models.BooleanField(db_index=True)),
                ("latency_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("checked_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("error_type", models.CharField(blank=True, default="", max_length=64)),
                ("error_message", models.CharField(blank=True, default="", max_length=255)),
                ("exit_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("test_url", models.URLField(max_length=500)),
                ("protocol", models.CharField(max_length=8)),
                ("proxy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="checks", to="proxy_web.proxy")),
            ],
            options={"ordering": ["-checked_at"], "indexes": [models.Index(fields=["proxy", "-checked_at"], name="proxy_web_p_proxy_i_128cc4_idx")]},
        ),
    ]
