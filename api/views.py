# api/views.py
from django.utils.timezone import now
from django.contrib.auth.models import User
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.db import IntegrityError

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
            return Response({"detail": "Missing or invalid date (YYYY-MM-DD)."}, status=400)

        style_id = request.query_params.get("style_id")

        qs = (
            Appointment.objects
            .select_related("style")
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
            Appointment.objects
            .select_related("style")
            .filter(user=self.request.user)
        )

class MeProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

# ---------------- STRIPE PAYMENT ----------------

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)

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
        return JsonResponse({"error": "Stripe is not configured."}, status=500)

    # Calculate amount from style's minimum price
    try:
        price_min = float(getattr(appt.style, "price_min", 0) or 0)
    except Exception:
        price_min = 0.0
    unit_amount_cents = int(round(price_min * 100))
    if unit_amount_cents <= 0:
        return JsonResponse({"error": "Invalid price for this service."}, status=400)

    # Prepare data for success_url enrichments
    amount_str = f"{unit_amount_cents / 100:.2f}"
    style_name = getattr(appt.style, "name", "Service")
    raw_first = (user.first_name or "").strip() or getattr(appt, "contact_name", "") or "there"
    first_name = raw_first.split(" ")[0]
    appt_dt = getattr(appt, "datetime", None)
    dt_iso = appt_dt.isoformat() if appt_dt else ""

    qs = (
        f"first={quote_plus(first_name)}"
        f"&style={quote_plus(style_name)}"
        f"&amount={quote_plus(amount_str)}"
        f"&dt={quote_plus(dt_iso)}"
    )

    customer_email = getattr(user, "email", None) or None

    try:
        kwargs = dict(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": style_name},
                        "unit_amount": unit_amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{settings.FRONTEND_BASE_URL}/payment-success?{qs}",
            cancel_url=f"{settings.FRONTEND_BASE_URL}/payment-cancelled",
            metadata={
                "appointment_id": str(appt.id),
                "user_id": str(appt.user_id or ""),
            },
        )
        if customer_email:
            kwargs["customer_email"] = customer_email

        session = stripe.checkout.Session.create(**kwargs)
        return JsonResponse({"url": session.url})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(["POST"])
def stripe_webhook(request):
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
    if not webhook_secret:
        return HttpResponse(status=400)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    except ValueError:
        return HttpResponse(status=400)

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata") or {}
        appt_id = metadata.get("appointment_id")
        amount_total = session.get("amount_total") or 0
        paid_amount = (amount_total or 0) / 100.0

        if appt_id:
            try:
                appt = Appointment.objects.get(id=int(appt_id))
                # Mark as paid (works whether you have 'is_paid' or 'status')
                if hasattr(appt, "is_paid"):
                    appt.is_paid = True
                if hasattr(appt, "status"):
                    appt.status = "paid"
                # If your model has an amount column, record it:
                if hasattr(appt, "amount") and not getattr(appt, "amount"):
                    appt.amount = paid_amount
                appt.save()

                try:
                    send_payment_confirmation(appt, paid_amount)
                except Exception:
                    pass
            except Appointment.DoesNotExist:
                pass

    return HttpResponse(status=200)