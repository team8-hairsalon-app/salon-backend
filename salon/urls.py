from django.contrib import admin
from django.urls import path, include

# ADD THESE IMPORTS
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("salon.api.urls")),
]

# Serve static files locally during development
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=(settings.BASE_DIR / "api" / "static")
    )
