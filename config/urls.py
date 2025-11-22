"""
config/urls.py – project-level URL configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),  # app API routes

    # --- Password reset endpoints (Django built-ins) ---
    path("auth/password/reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("auth/password/reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("auth/password/reset/confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("auth/password/reset/complete/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]