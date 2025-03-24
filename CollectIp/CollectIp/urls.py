"""CollectIp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from index.views import (
    login_view, register_view, ip_pool_view,
    ip_manage_view, proxy_settings_view,
    monitoring_view, operation_log_view,
    wechat_view, wechat_overview, article_manage,
    media_library, data_analysis, wechat_settings,
    douban_view, douban_overview, movie_list,
    tv_list, data_trend, douban_settings,
    crawl_once_view,
    score_once_view,
    crawl_movie_view
)
from django.contrib.auth.decorators import login_required
from index import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
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
    path('douban/', douban_view, name='douban'),
    path('douban/overview/', douban_overview, name='douban_overview'),
    path('douban/movies/', movie_list, name='movie_list'),
    path('douban/tv/', tv_list, name='tv_list'),
    path('douban/trend/', data_trend, name='data_trend'),
    path('douban/settings/', douban_settings, name='douban_settings'),
    path('crawl_once/', crawl_once_view, name='crawl_once'),
    path('score_once/', score_once_view, name='score_once'),
    path('crawl_movie/', crawl_movie_view, name='crawl_movie'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
