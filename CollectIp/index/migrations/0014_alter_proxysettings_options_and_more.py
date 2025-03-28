# Generated by Django 5.1.7 on 2025-03-23 21:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0013_proxysettings'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='proxysettings',
            options={},
        ),
        migrations.AlterField(
            model_name='proxysettings',
            name='crawler_interval',
            field=models.IntegerField(default=3600),
        ),
        migrations.AlterField(
            model_name='proxysettings',
            name='min_score',
            field=models.IntegerField(default=10),
        ),
        migrations.AlterField(
            model_name='proxysettings',
            name='score_interval',
            field=models.IntegerField(default=1800),
        ),
        migrations.AlterModelTable(
            name='proxysettings',
            table='proxy_settings',
        ),
    ]
