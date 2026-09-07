"""
URL configuration for pet_feeder_django project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

from api.web_views import not_found

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
    path("api/", include("api.urls")),
    path("", include("api.web_urls")),
]

handler404 = not_found

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
