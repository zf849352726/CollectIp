"""CollectIp URL Configuration - 优化版本

优化版本 - 移除了admin和调试工具栏相关的URL配置
"""
from django.urls import path, include
from index.views import (
    login_view, register_view, ip_pool_view,
    ip_manage_view, proxy_settings_view,
    monitoring_view, operation_log_view,
    wechat_view, wechat_overview, article_manage,
    media_library, data_analysis, wechat_settings,
    douban, douban_overview, movie_list, movie_detail,
    tv_list, data_trend, douban_settings,
    crawl_once_view,
    score_once_view,
    crawl_movie,
    update_movie_wordcloud,
    toggle_movie_published,
    get_last_crawl_status,
    create_collection, get_collection, update_collection, delete_collection,
    logs_view, get_log_content, download_log,
    delete_movie,
    check_crawler_task,
)
from django.contrib.auth.decorators import login_required
from index import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 移除admin路径
    # path('admin/', admin.site.urls),
    path('index/', login_required(views.index), name='index'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('', login_required(views.index), name='home'),  # 根路径
    path('ip_pool/', ip_pool_view, name='ip_pool'),
    path('ip_pool/manage/', ip_manage_view, name='ip_manage'),
    path('proxy_settings/', proxy_settings_view, name='proxy_settings'),
    path('ip_pool/monitoring/', monitoring_view, name='monitoring'),
    path('ip_pool/logs/', operation_log_view, name='operation_log'),
    path('wechat/', wechat_view, name='wechat'),
    path('wechat/overview/', wechat_overview, name='wechat_overview'),
    path('wechat/articles/', article_manage, name='article_manage'),
    path('wechat/media/', media_library, name='media_library'),
    path('wechat/analysis/', data_analysis, name='data_analysis'),
    path('wechat/settings/', wechat_settings, name='wechat_settings'),
    path('collections/create/', create_collection, name='create_collection'),
    path('collections/<int:collection_id>/', get_collection, name='get_collection'),
    path('collections/<int:collection_id>/update/', update_collection, name='update_collection'),
    path('collections/<int:collection_id>/delete/', delete_collection, name='delete_collection'),
    path('douban/', douban, name='douban'),
    path('douban/overview/', douban_overview, name='douban_overview'),
    path('douban/movies/', movie_list, name='movie_list'),
    path('douban/movies/<int:movie_id>/', movie_detail, name='movie_detail'),
    path('douban/movies/<int:movie_id>/toggle_published/', toggle_movie_published, name='toggle_movie_published'),
    path('douban/tv/', tv_list, name='tv_list'),
    path('douban/trend/', data_trend, name='data_trend'),
    path('douban/settings/', douban_settings, name='douban_settings'),
    path('crawl_once/', crawl_once_view, name='crawl_once'),
    path('score_once/', score_once_view, name='score_once'),
    path('crawl_status/', get_last_crawl_status, name='crawl_status'),
    path('crawl_movie/', crawl_movie, name='crawl_movie'),
    path('logs/', logs_view, name='logs_view'),
    path('api/logs/content/', get_log_content, name='get_log_content'),
    path('api/logs/download/', download_log, name='download_log'),
    path('douban/movies/<int:movie_id>/delete/', delete_movie, name='delete_movie'),
    path('check_task/', check_crawler_task, name='check_task'),
]

# 非调试模式下的静态文件配置
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 移除调试工具栏路径
# if settings.DEBUG:
#     import debug_toolbar
#     urlpatterns += [
#         path('__debug__/', include(debug_toolbar.urls)),
#     ] 