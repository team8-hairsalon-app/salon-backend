from rest_framework import serializers
from .models.appointment import Appointment
from django.utils import timezone

class AppointmentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "user",
            "customer_name",
            "customer_email",
            "style_id",
            "style_name",
            "appointment_time",
            "notes",
            "status",
            "created",
            "modified",
        ]
        read_only_fields = ("user", "status", "created", "modified")

    def validate_appointment_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("appointment_time must be in the future")
        return value
