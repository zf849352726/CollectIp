from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "favicon.ico",
        RedirectView.as_view(url="/static/proxy_web/favicon.svg", permanent=True),
    ),
    path("", include("proxy_web.urls")),
]
