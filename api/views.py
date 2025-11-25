# api/views.py
from django.utils.timezone import now, localtime
from django.contrib.auth.models import User
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta

from rest_framework import generics, viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import (
    action,
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.utils.dateparse import parse_date

import stripe
from urllib.parse import quote_plus

from .serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    StyleSerializer,
    AppointmentSerializer,
)
from .models import Style, Appointment
from .notifications import send_booking_confirmation_email

import os
from math import ceil


# ---------------- AUTH ----------------
class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["name"] = f"{user.first_name} {user.last_name}".strip()
        return token

    def validate(self, attrs):
        supplied = attrs.get("username")
        if supplied and "@" in supplied:
            try:
                u = User.objects.get(email__iexact=supplied)
                attrs["username"] = u.username
            except User.DoesNotExist:
                pass
        return super().validate(attrs)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class MyTokenRefreshView(TokenRefreshView):
    pass


# ---------------- STYLES ----------------
class StyleViewSet(viewsets.ModelViewSet):
    queryset = Style.objects.all().order_by("name")
    serializer_class = StyleSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


# ---------------- APPOINTMENTS ----------------
class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer

    def get_permissions(self):
        if self.action in ("create", "taken"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related("style", "user")
        if user.is_authenticated and user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(user=user)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        try:
            appt = serializer.save(user=user)
        except IntegrityError:
            from rest_framework.exceptions import APIException

            err = APIException(
                "An appointment for this service, date, and time already exists."
            )
            err.status_code = 409
            raise err

        #Send email confirmation
        try:
            send_booking_confirmation_email(appt)
        except Exception:
            pass

   # ---------------- TAKEN SLOTS (LOCAL TIME, FULL DETAILS) ----------------
    @action(
        detail=False,
        methods=["get"],
        permission_classes=[AllowAny],
        authentication_classes=[],
        url_path="taken",
    )
    def taken(self, request):
        date_str = request.query_params.get("date")
        if not date_str or not parse_date(date_str):
            return Response(
                {"detail": "Missing or invalid date (YYYY-MM-DD)."},
                status=400
            )

        style_id = request.query_params.get("style_id")

        qs = (
            Appointment.objects.select_related("style")
            .filter(datetime__date=date_str)
            .exclude(status__iexact="cancelled")
        )
        if style_id:
            qs = qs.filter(style_id=style_id)

        taken = []

        for appt in qs:
            # Convert to local timezone
            local_dt = localtime(appt.datetime)
            start_time = local_dt.strftime("%H:%M")

            duration = appt.style.duration_mins or 60
            blocks = ceil(duration / 30)

            # Generate all affected 30-minute blocks
            for i in range(blocks):
                slot_dt = local_dt + timedelta(minutes=i * 30)
                hhmm = slot_dt.strftime("%H:%M")

                taken.append({
                    "time": hhmm,
                    "duration": duration,
                    "contact_email": appt.contact_email,
                    "contact_phone": appt.contact_phone,
                })

        return Response({
            "date": date_str,
            "style_id": style_id,
            "taken": taken
        })

    # ---------------- UPCOMING (LOCAL TIME) ----------------
    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def upcoming(self, request):
        qs = (
            self.get_queryset()
            .filter(datetime__gte=now())
            .exclude(status__iexact="cancelled")
            .order_by("datetime")
        )

        # Convert all datetimes to local before serialization
        appts = []
        for appt in qs:
            local_dt = localtime(appt.datetime)
            appt.datetime = local_dt.replace(second=0, microsecond=0)
            appts.append(appt)

        return Response(AppointmentSerializer(appts, many=True).data)

    # ---------------- CANCEL APPOINTMENT ----------------
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def cancel(self, request, pk=None):
        appt = self.get_object()
        if appt.status != "cancelled":
            appt.status = "cancelled"
            appt.save(update_fields=["status"])
        appt.datetime = localtime(appt.datetime)
        return Response(AppointmentSerializer(appt).data)


# ---------------- PROFILE ----------------
class MeAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = (
            Appointment.objects.select_related("style")
            .filter(user=self.request.user)
        )
        for appt in qs:
            appt.datetime = localtime(appt.datetime)
        return qs


class MeProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


# ---------------- STRIPE PAYMENT ----------------

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


def _frontend_base_url() -> str:
    base = os.environ.get("FRONTEND_BASE_URL", "").strip()
    if not base:
        base = "https://salon-frontend-pink.vercel.app"
    return base.rstrip("/")


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_checkout_session(request, appointment_id: int):

    try:
        appt = Appointment.objects.select_related("style", "user").get(id=appointment_id)
    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Appointment not found."}, status=404)

    user = request.user
    if not user.is_staff and appt.user_id != user.id:
        return JsonResponse({"error": "Not allowed."}, status=403)

    try:
        price_min = float(appt.style.price_min or 0)
    except Exception:
        price_min = 0.0

    unit_amount = int(round(price_min * 100))
    if unit_amount <= 0:
        return JsonResponse({"error": "Invalid price for this service."}, status=400)

    style_name = appt.style.name
    first_name = (user.first_name or appt.contact_name or "there").split(" ")[0]

    # Convert datetime to local before sending to frontend
    dt_local = localtime(appt.datetime).isoformat()

    qs = (
        f"appt={appt.id}"
        f"&first={quote_plus(first_name)}"
        f"&style={quote_plus(style_name)}"
        f"&amount={quote_plus(f'{unit_amount/100:.2f}')}"
        f"&dt={quote_plus(dt_local)}"
    )

    frontend = _frontend_base_url()

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": style_name},
                        "unit_amount": unit_amount,
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{frontend}/payment-success?{qs}",
            cancel_url=f"{frontend}/payment-cancelled",
            customer_email=user.email,
            metadata={"appointment_id": str(appt.id)},
        )

        return JsonResponse({"url": session.url})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ---------------- STRIPE WEBHOOK ----------------

@csrf_exempt
@api_view(["POST"])
def stripe_webhook(request):

    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        return HttpResponse(status=400)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        return HttpResponse(status=400)

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        appt_id = session.get("metadata", {}).get("appointment_id")
        amount_total = (session.get("amount_total") or 0) / 100.0

        if appt_id:
            try:
                appt = Appointment.objects.get(id=int(appt_id))
                appt.status = "paid"
                appt.is_paid = True
                appt.amount = amount_total
                appt.save()

            except Appointment.DoesNotExist:
                pass

    return HttpResponse(status=200)
