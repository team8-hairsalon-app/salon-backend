from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from .views import AppointmentViewSet
router = routers.SimpleRouter()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(router.urls)),
]
