# salon/api/views.py
from django.http import JsonResponse
from django.utils import timezone
from django.templatetags.static import static  # <-- ADD THIS
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models.appointment import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all().order_by("-appointment_time")
    serializer_class = AppointmentSerializer
    permission_classes = [AllowAny]  # swap to IsAuthenticated when ready

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
        now = timezone.now()
        qs = self.queryset.filter(appointment_time__gte=now).order_by("appointment_time")
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            qs = self.queryset.filter(user=user).order_by("-appointment_time")
        else:
            qs = Appointment.objects.none()
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="start_checkout")
    def start_checkout(self, request, pk=None):
        # Stripe integration can go here later.
        # Returning None URL keeps the UI graceful for now.
        return Response({"url": None})


def _img(request, rel_path: str) -> str:
    """Return an absolute URL for a static asset."""
    return request.build_absolute_uri(static(rel_path))


def styles_list(request):
    """
    Temporary styles endpoint to unblock the frontend.
    Now serves local static images from salon/api/static/images/.
    """
    styles = [
        {
            "id": 1,
            "name": "Classic Cut",
            "category": "cut",
            "priceMin": 25,
            "priceMax": 40,
            "durationMins": 30,
            "imageUrl": _img(request, "images/classic_cut.png"),
        },
        {
            "id": 2,
            "name": "Skin Fade",
            "category": "cut",
            "priceMin": 30,
            "priceMax": 50,
            "durationMins": 45,
            "imageUrl": _img(request, "images/skin_fade.png"),
        },
        {
            "id": 3,
            "name": "Single-Process Color",
            "category": "color",
            "priceMin": 70,
            "priceMax": 110,
            "durationMins": 90,
            "imageUrl": _img(request, "images/single_process_color.png"),
        },
        {
            "id": 4,
            "name": "Foil Highlights",
            "category": "color",
            "priceMin": 95,
            "priceMax": 160,
            "durationMins": 120,
            "imageUrl": _img(request, "images/foil_highlights.png"),
        },
        {
            "id": 5,
            "name": "Box Braids",
            "category": "braids",
            "priceMin": 120,
            "priceMax": 240,
            "durationMins": 180,
            # NOTE: your file is singular: box_braid.png
            "imageUrl": _img(request, "images/box_braid.png"),
        },
        {
            "id": 6,
            "name": "Blowout & Style",
            "category": "styling",
            "priceMin": 35,
            "priceMax": 60,
            "durationMins": 45,
            "imageUrl": _img(request, "images/blowout_style.png"),
        },
    ]
    return JsonResponse(styles, safe=False)
