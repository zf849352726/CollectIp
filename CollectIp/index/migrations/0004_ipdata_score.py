# Generated by Django 4.1 on 2024-07-23 15:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0003_alter_ipdata_ping'),
    ]

    operations = [
        migrations.AddField(
            model_name='ipdata',
            name='score',
            field=models.IntegerField(default=100, verbose_name='分数'),
        ),
    ]
