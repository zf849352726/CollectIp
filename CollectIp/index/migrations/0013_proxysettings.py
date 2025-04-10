# Generated by Django 4.1 on 2025-03-23 11:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0012_remove_ipdata_delay_remove_ipdata_type_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProxySettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('crawler_interval', models.IntegerField(default=3600, help_text='爬虫多久运行一次', verbose_name='爬虫采集间隔(秒)')),
                ('score_interval', models.IntegerField(default=1800, help_text='IP池中的代理多久评分一次', verbose_name='IP评分间隔(秒)')),
                ('min_score', models.IntegerField(default=10, help_text='低于此分数的IP将被删除', verbose_name='最低分数阈值')),
            ],
            options={
                'verbose_name': '代理设置',
                'verbose_name_plural': '代理设置',
            },
        ),
    ]
