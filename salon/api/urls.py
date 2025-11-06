# salon/api/urls.py
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import SimpleRouter

from .views import AppointmentViewSet, styles_list  # added styles_list

def ping(request):
    return JsonResponse({"ok": True, "service": "salon-backend"})

router = SimpleRouter()
router.register(r"appointments", AppointmentViewSet, basename="appointment")

urlpatterns = [
    path("ping/", ping),
    path("styles/", styles_list),  #  new route for frontend to load styles
    path("", include(router.urls)),
]
