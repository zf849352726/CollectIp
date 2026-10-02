from django.urls import path

from . import views

app_name = "proxy_web"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("proxies/<int:pk>/", views.proxy_detail, name="proxy_detail"),
    path("api/status/", views.api_status, name="api_status"),
    path("api/proxies/", views.api_proxies, name="api_proxies"),
    path("api/proxies/random/", views.api_random_proxy, name="api_random_proxy"),
    path("api/jobs/collect/", views.start_collect, name="start_collect"),
    path("api/jobs/score/", views.start_score, name="start_score"),
    path("settings/", views.update_settings, name="update_settings"),
    path("health/", views.health, name="health"),
]
