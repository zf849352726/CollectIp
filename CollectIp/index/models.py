from django.db import models
from django.utils import timezone


# Create your models here.

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
    poster_url = models.URLField(max_length=500, null=True, blank=True, verbose_name='海报URL')
    summary = models.TextField(null=True, blank=True, verbose_name='剧情简介')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_published = models.BooleanField(default=False, verbose_name='是否已发表')

    class Meta:
        verbose_name = '电影'
        verbose_name_plural = verbose_name
        ordering = ['-rating', '-rating_count']

    def __str__(self):
        return self.title

class ProxySettings(models.Model):
    crawler_interval = models.IntegerField(default=3600)  # 爬虫间隔（秒）
    score_interval = models.IntegerField(default=1800)   # 评分间隔（秒）
    min_score = models.IntegerField(default=10)         # 最低分数
    auto_crawler = models.BooleanField(default=False)   # 是否启用自动爬虫
    auto_score = models.BooleanField(default=False)     # 是否启用自动评分
    captcha_retries = models.IntegerField(default=5)    # 验证码最大重试次数

    class Meta:
        db_table = 'proxy_settings'

class DoubanSettings(models.Model):
    """豆瓣数据采集设置"""
    crawl_interval = models.IntegerField(default=60, help_text="采集间隔（分钟）")
    movie_count = models.IntegerField(default=10, help_text="电影采集数量")
    tv_count = models.IntegerField(default=5, help_text="电视剧采集数量")
    
    class Meta:
        verbose_name = "豆瓣设置"
        verbose_name_plural = "豆瓣设置"
        
    def __str__(self):
        return "豆瓣采集设置"

class Collection(models.Model):
    """电影合集模型"""
    COLLECTION_TYPE_CHOICES = (
        ('movie', '电影合集'),
        ('tv', '剧集合集'),
        ('article', '文章合集'),
        ('mixed', '混合合集'),
    )
    
    title = models.CharField(max_length=200, verbose_name='合集标题')
    description = models.TextField(blank=True, null=True, verbose_name='合集描述')
    collection_type = models.CharField(
        max_length=20, 
        choices=COLLECTION_TYPE_CHOICES, 
        default='movie',
        verbose_name='合集类型'
    )
    cover_image = models.URLField(blank=True, null=True, verbose_name='封面图片URL')
    is_published = models.BooleanField(default=False, verbose_name='是否发布')
    movies = models.ManyToManyField(Movie, related_name='collections', blank=True, verbose_name='电影列表')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '合集'
        verbose_name_plural = '合集列表'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.title
    
    @property
    def item_count(self):
        """获取合集包含的项目数量"""
        return self.movies.count()
    
    @property
    def get_collection_type_display(self):
        """获取合集类型的显示名称"""
        return dict(self.COLLECTION_TYPE_CHOICES).get(self.collection_type, '未知类型')
