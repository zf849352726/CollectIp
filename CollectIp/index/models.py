from django.db import models
from django.utils import timezone


# Create your models here.


# class IpData(models.Model):
#     server = models.CharField(max_length=21, unique=True, verbose_name='服务器', default='Unknown Server')
#     ping = models.DecimalField(max_digits=6, decimal_places=4, verbose_name='延迟ms', blank=True, null=True)
#     speed = models.DecimalField(max_digits=7, decimal_places=2, verbose_name='速度', blank=True, null=True)
#     uptime1 = models.CharField(max_length=5, verbose_name='上传时间1', default='N/A')
#     uptime2 = models.CharField(max_length=5, verbose_name='上传时间2', default='N/A')
#     type_data = models.CharField(max_length=20, verbose_name='类型', default='Unknown')
#     country = models.CharField(max_length=20, verbose_name='国家', default='Unknown')
#     ssl = models.CharField(max_length=50, verbose_name='SSL', default='N/A')
#     conn = models.CharField(max_length=50, verbose_name='CONN.', default='N/A')
#     post = models.CharField(max_length=50, verbose_name='POST', default='N/A')
#     last_work_time = models.CharField(max_length=30, verbose_name='最近工作时间', default='N/A')
#     score = models.IntegerField(verbose_name='分数', default=100)

class IpData(models.Model):
    server = models.CharField(max_length=21, unique=True, verbose_name='服务器', default='Unknown Server')
    ping = models.DecimalField(max_digits=6, decimal_places=4, verbose_name='延迟ms', blank=True, null=True)
    speed = models.DecimalField(max_digits=7, decimal_places=2, verbose_name='速度', blank=True, null=True)
    uptime1 = models.CharField(max_length=5, verbose_name='上传时间1', default='N/A')
    uptime2 = models.CharField(max_length=5, verbose_name='上传时间2', default='N/A')
    type_data = models.CharField(max_length=20, verbose_name='类型', default='Unknown')
    country = models.CharField(max_length=20, verbose_name='国家', default='Unknown')
    ssl = models.CharField(max_length=50, verbose_name='SSL', default='N/A')
    conn = models.CharField(max_length=50, verbose_name='CONN.', default='N/A')
    post = models.CharField(max_length=50, verbose_name='POST', default='N/A')
    last_work_time = models.CharField(max_length=30, verbose_name='最近工作时间', default='N/A')
    score = models.IntegerField(verbose_name='分数', default=100)
    created_at = models.DateTimeField(verbose_name='创建时间', default=timezone.now)
    updated_at = models.DateTimeField(verbose_name='更新时间', default=timezone.now)

    class Meta:
        verbose_name = 'IP池'
        verbose_name_plural = verbose_name
        ordering = ['-score', '-updated_at']

    def __str__(self):
        return f"{self.server} - {self.country}"

class Movie(models.Model):
    title = models.CharField(max_length=200, verbose_name='电影名称')
    director = models.CharField(max_length=100, verbose_name='导演')
    actors = models.TextField(verbose_name='主演')
    year = models.CharField(max_length=20, verbose_name='上映年份')
    rating = models.DecimalField(max_digits=3, decimal_places=1, verbose_name='评分')
    rating_count = models.IntegerField(verbose_name='评分人数')
    genre = models.CharField(max_length=100, verbose_name='类型')
    region = models.CharField(max_length=100, verbose_name='国家/地区')
    duration = models.CharField(max_length=50, verbose_name='片长')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '电影'
        verbose_name_plural = verbose_name
        ordering = ['-rating', '-rating_count']

    def __str__(self):
        return self.title
