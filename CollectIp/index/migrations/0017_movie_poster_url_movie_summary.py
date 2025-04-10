# Generated by Django 5.1.7 on 2025-03-26 22:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0016_doubansettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='movie',
            name='poster_url',
            field=models.URLField(blank=True, max_length=500, null=True, verbose_name='海报URL'),
        ),
        migrations.AddField(
            model_name='movie',
            name='summary',
            field=models.TextField(blank=True, null=True, verbose_name='剧情简介'),
        ),
    ]
