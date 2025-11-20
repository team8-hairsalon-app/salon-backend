# api/views.py
from django.utils.timezone import now
from django.contrib.auth.models import User
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt

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
from .notifications import send_booking_confirmation, send_payment_confirmation
import os

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
    """
    - Anyone can create.
    - Authenticated users can list/view/modify their own.
    - Staff can view all.
    """

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
                "An appointment for this service, date, and time already exists for you."
            )
            err.status_code = 409
            raise err

        # fire-and-forget confirmation
        try:
            send_booking_confirmation(appt)
        except Exception:
            pass

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
                {"detail": "Missing or invalid date (YYYY-MM-DD)."}, status=400
            )

        style_id = request.query_params.get("style_id")

        qs = (
            Appointment.objects.select_related("style")
            .filter(datetime__date=date_str)
            .exclude(status="cancelled")
        )
        if style_id:
            qs = qs.filter(style_id=style_id)

        seen = set()
        taken = []
        for appt in qs:
            hhmm = appt.datetime.strftime("%H:%M")
            if hhmm not in seen:
                seen.add(hhmm)
                taken.append(hhmm)

        return Response({"date": date_str, "style_id": style_id, "taken": taken})

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def upcoming(self, request):
        """
        Future appointments for this user, excluding cancelled ones.
        """
        qs = (
            self.get_queryset()
            .filter(datetime__gte=now())
            .exclude(status="cancelled")
            .order_by("datetime")
        )
        return Response(AppointmentSerializer(qs, many=True).data)

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
        return Response(AppointmentSerializer(appt).data)


# ---------------- PROFILE (me) ----------------


class MeAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Appointment.objects.select_related("style")
            .filter(user=self.request.user)
        )


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

    if not stripe.api_key:
        print("Stripe API key missing")
        return JsonResponse({"error": "Stripe is not configured."}, status=500)

    try:
        price_min = float(appt.style.price_min or 0)
    except Exception:
        price_min = 0.0

    unit_amount = int(round(price_min * 100))
    if unit_amount <= 0:
        return JsonResponse({"error": "Invalid price for this service."}, status=400)

    amount_str = f"{unit_amount / 100:.2f}"
    style_name = appt.style.name
    first_name = (user.first_name or appt.contact_name or "there").split(" ")[0]
    dt_iso = appt.datetime.isoformat() if appt.datetime else ""

    qs = (
        f"appt={appt.id}"
        f"&first={quote_plus(first_name)}"
        f"&style={quote_plus(style_name)}"
        f"&amount={quote_plus(amount_str)}"
        f"&dt={quote_plus(dt_iso)}"
    )

    frontend = _frontend_base_url()
    print("FRONTEND_BASE_URL =", frontend)
    print("Creating Stripe session:")
    print("    User:", user.email)
    print("    Style:", style_name)
    print("    Price (cents):", unit_amount)
    print("    Appointment ID:", appt.id)

    # ---------------- Create Stripe session ----------------
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

        print("Stripe session created:", session.id)
        return JsonResponse({"url": session.url})

    except Exception as e:
        print("Stripe error:", str(e))
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(["POST"])
def stripe_webhook(request):

    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        print("No STRIPE_WEBHOOK_SECRET found")
        return HttpResponse(status=400)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        print("Webhook signature invalid")
        return HttpResponse(status=400)

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        appt_id = session.get("metadata", {}).get("appointment_id")
        amount_total = (session.get("amount_total") or 0) / 100.0

        print(f"Checkout complete for Appointment {appt_id}, amount ${amount_total}")

        if appt_id:
            try:
                appt = Appointment.objects.get(id=int(appt_id))

                # Mark paid
                if hasattr(appt, "is_paid"):
                    appt.is_paid = True
                if hasattr(appt, "status"):
                    appt.status = "paid"
                if hasattr(appt, "amount") and not appt.amount:
                    appt.amount = amount_total

                appt.save()

            except Appointment.DoesNotExist:
                print("Appointment missing for webhook")

    return HttpResponse(status=200)
