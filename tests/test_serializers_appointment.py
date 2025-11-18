import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from django.utils import timezone

from api.models import Style, Appointment
from api.serializers import AppointmentSerializer

@pytest.fixture
def style():
    return Style.objects.create(
        name="Twists",
        category="braids",
        price_min=80,
        price_max=200,
        duration_mins=120,
    )


@pytest.mark.django_db
def test_appointment_serializer_is_paid_flag(style):
    appt = Appointment(
        style=style,
        datetime=timezone.now(),
        status="paid",
    )
    serializer = AppointmentSerializer(appt)

    assert serializer.data["is_paid"] is True


@pytest.mark.django_db
def test_appointment_serializer_amount_fallback(style):
    appt = Appointment(
        style=style,
        datetime=timezone.now(),
        status="pending",
    )
    serializer = AppointmentSerializer(appt)

    assert serializer.data["amount"] == 80


@pytest.mark.django_db
def test_appointment_validation_guest_requires_name(style):
    serializer = AppointmentSerializer(
        data={
            "style": style.id,
            "datetime": timezone.now(),
            "contact_email": "test@example.com"
        }
    )
    assert not serializer.is_valid()
    assert "contact_name" in serializer.errors


@pytest.mark.django_db
def test_appointment_validation_guest_requires_contact_info(style):
    serializer = AppointmentSerializer(
        data={
            "style": style.id,
            "datetime": timezone.now(),
            "contact_name": "Jane",
            "contact_email": "",
            "contact_phone": ""
        }
    )
    assert not serializer.is_valid()
    assert "contact_email" in serializer.errors
    assert "contact_phone" in serializer.errors


@pytest.mark.django_db
def test_appointment_validation_signed_in_autofills(style):
    user = User.objects.create_user(
        username="testuser",
        email="user@example.com",
        first_name="John",
        last_name="Doe"
    )

    request = APIRequestFactory().post("/")
    request.user = user

    serializer = AppointmentSerializer(
        context={"request": request},
        data={
            "style": style.id,
            "datetime": timezone.now(),
            "contact_name": "",
            "contact_email": "",
        }
    )

    assert serializer.is_valid(), serializer.errors
    validated = serializer.validated_data

    assert validated["contact_name"] == "John Doe"
    assert validated["contact_email"] == "user@example.com"
