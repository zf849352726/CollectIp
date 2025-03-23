from django.contrib import admin

# Register your models here.
from .models import IpData, Movie #这个需要我们自己导入相应的模型类（数据表）

@admin.register(IpData)
class IpDataAdmin(admin.ModelAdmin):
    list_display = ('server', 'country', 'type_data', 'ping', 'speed', 'score', 'last_work_time')
    list_filter = ('country', 'type_data', 'ssl')
    search_fields = ('server', 'country')
    ordering = ('-score',)

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'director', 'year', 'rating', 'rating_count')
    list_filter = ('year', 'genre', 'region')
    search_fields = ('title', 'director', 'actors')
    ordering = ('-rating',)