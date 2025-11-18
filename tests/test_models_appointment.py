import pytest
from django.contrib.auth.models import User
from api.models import Style, Appointment
from django.utils import timezone
from datetime import timedelta
from django.db import IntegrityError

@pytest.fixture
def style():
    return Style.objects.create(
        name="Cornrows",
        category="braids",
        price_min=50,
        price_max=120,
        duration_mins=90,
    )

@pytest.fixture
def user():
    return User.objects.create_user(username="test", password="pass123")


@pytest.mark.django_db
def test_appointment_str_user(style, user):
    dt = timezone.now()
    appt = Appointment.objects.create(
        user=user,
        style=style,
        datetime=dt,
    )
    assert user.username in str(appt)
    assert style.name in str(appt)


@pytest.mark.django_db
def test_appointment_str_guest(style):
    dt = timezone.now()
    appt = Appointment.objects.create(
        style=style,
        datetime=dt,
        contact_name="Jane Doe",
    )
    assert "Jane Doe" in str(appt)


@pytest.mark.django_db
def test_unique_constraint_signed_in_user(style, user):
    dt = timezone.now()

    Appointment.objects.create(
        user=user,
        style=style,
        datetime=dt,
    )

    with pytest.raises(IntegrityError):
        Appointment.objects.create(
            user=user,
            style=style,
            datetime=dt,
        )


@pytest.mark.django_db
def test_unique_constraint_guest_email(style):
    dt = timezone.now()

    Appointment.objects.create(
        user=None,
        style=style,
        datetime=dt,
        contact_email="guest@example.com",
    )

    with pytest.raises(IntegrityError):
        Appointment.objects.create(
            user=None,
            style=style,
            datetime=dt,
            contact_email="guest@example.com",
        )


@pytest.mark.django_db
def test_guest_no_email_does_not_trigger_constraint(style):
    dt = timezone.now()

    Appointment.objects.create(
        user=None,
        style=style,
        datetime=dt,
        contact_email="",
    )

    Appointment.objects.create(
        user=None,
        style=style,
        datetime=dt,
        contact_email="",
    )


@pytest.mark.django_db
def test_user_and_guest_do_not_conflict(style, user):
    dt = timezone.now()

    Appointment.objects.create(
        user=user,
        style=style,
        datetime=dt,
    )

    Appointment.objects.create(
        user=None,
        style=style,
        datetime=dt,
        contact_email="guest@example.com",
    )
