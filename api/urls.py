from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    # Core resources
    StyleViewSet,
    AppointmentViewSet,
    MeAppointmentsView,
    MeProfileView,

    # Auth
    RegisterView,
    MyTokenObtainPairView,
    MyTokenRefreshView,

    # Stripe
    create_checkout_session,
    stripe_webhook,
)

# DRF router for ViewSets
router = DefaultRouter()
router.register(r"styles", StyleViewSet, basename="style")
router.register(r"appointments", AppointmentViewSet, basename="appointment")

urlpatterns = [
    # ---------- Authentication ----------
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", MyTokenRefreshView.as_view(), name="token_refresh"),

    # ---------- Current-user endpoints ----------
    path("me/appointments/", MeAppointmentsView.as_view(), name="me_appointments"),
    path("me/profile/", MeProfileView.as_view(), name="me_profile"),

    # ---------- Stripe payments ----------
    # Function-view endpoint your frontend should call
    path(
        "checkout/create-session/<int:appointment_id>/",
        create_checkout_session,
        name="checkout_create_session",
    ),
    path("webhooks/stripe/", stripe_webhook, name="stripe_webhook"),

    # ---------- API root (viewsets) ----------
    path("", include(router.urls)),
]