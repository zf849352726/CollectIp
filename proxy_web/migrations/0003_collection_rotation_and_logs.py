from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("proxy_web", "0002_monitoring_and_jobs")]

    operations = [
        migrations.AddField(
            model_name="proxy",
            name="collection_failures",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="proxy",
            name="collection_last_error",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="proxy",
            name="collection_successes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="proxy",
            name="last_collection_used_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="allow_direct_fallback",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="collection_max_delay_ms",
            field=models.PositiveIntegerField(default=1500),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="collection_max_runtime",
            field=models.PositiveIntegerField(default=300),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="collection_min_delay_ms",
            field=models.PositiveIntegerField(default=500),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="log_retention_days",
            field=models.PositiveSmallIntegerField(default=30),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="collection_proxy_attempts",
            field=models.PositiveSmallIntegerField(default=3),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="collection_proxy_min_score",
            field=models.PositiveSmallIntegerField(default=60),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="collection_retry_backoff",
            field=models.PositiveSmallIntegerField(default=15),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="use_proxy_for_collection",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="OperationLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("DEBUG", "调试"),
                            ("INFO", "信息"),
                            ("WARNING", "警告"),
                            ("ERROR", "错误"),
                        ],
                        db_index=True,
                        max_length=8,
                    ),
                ),
                ("module", models.CharField(db_index=True, max_length=32)),
                ("event", models.CharField(db_index=True, max_length=64)),
                ("message", models.TextField()),
                ("details", models.JSONField(blank=True, default=dict)),
                (
                    "proxy_server",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        max_length=64,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "job",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="logs",
                        to="proxy_web.backgroundjob",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
