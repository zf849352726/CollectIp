from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Proxy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("server", models.CharField(max_length=64, unique=True, verbose_name="代理地址")),
                ("ping", models.FloatField(blank=True, null=True, verbose_name="源站延迟")),
                ("speed", models.FloatField(blank=True, null=True, verbose_name="源站速度")),
                ("uptime1", models.CharField(default="N/A", max_length=16)),
                ("uptime2", models.CharField(default="N/A", max_length=16)),
                ("proxy_type", models.CharField(default="Unknown", max_length=32)),
                ("country", models.CharField(default="Unknown", max_length=64)),
                ("ssl", models.CharField(default="N/A", max_length=128)),
                ("conn", models.CharField(default="N/A", max_length=128)),
                ("post", models.CharField(default="N/A", max_length=128)),
                ("source_last_work_time", models.CharField(default="N/A", max_length=64)),
                ("score", models.PositiveSmallIntegerField(db_index=True, default=50)),
                ("is_available", models.BooleanField(db_index=True, default=False)),
                ("latency_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("consecutive_failures", models.PositiveIntegerField(default=0)),
                ("last_checked_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("last_error", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-is_available", "-score", "latency_ms", "server"]},
        )
    ]
