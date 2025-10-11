from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models.appointment import Appointment
from .serializers import AppointmentSerializer
from datetime import datetime
from rest_framework.decorators import action
from rest_framework.response import Response

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all().order_by("-appointment_time")
    serializer_class = AppointmentSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated if needed

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["user", "status", "customer_email"]
    ordering_fields = ["appointment_time", "created"]
    ordering = ["-appointment_time"]

    def perform_create(self, serializer):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            serializer.save(user=user)
        else:
            serializer.save()

    @action(detail=False, methods=["get"], url_path="upcoming")
    def upcoming_appointments(self, request):
        # Return only upcoming appointments
        now = datetime.now()
        upcoming = self.queryset.filter(appointment_time__gte=now).order_by("appointment_time")
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)