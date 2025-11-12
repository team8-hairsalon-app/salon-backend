from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse  #  Added for the welcome message

# ADD THESE IMPORTS
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    #  Root endpoint with a friendly JSON message
    path("", lambda request: JsonResponse({"message": "Salon Backend API is running successfully 🚀"})),

    # Admin and API routes
    path("admin/", admin.site.urls),
    path("api/", include("salon.api.urls")),
]

# Serve static files locally during development
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=(settings.BASE_DIR / "api" / "static")
    )
