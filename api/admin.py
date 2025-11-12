from django.contrib import admin
from .models import Style, Appointment

@admin.register(Style)
class StyleAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price_min", "price_max", "duration_mins", "rating_avg")
    search_fields = ("name", "category")

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("user", "style", "datetime", "status", "created_at")
    list_filter = ("status", "datetime")
    search_fields = ("user__email", "style__name", "notes")
