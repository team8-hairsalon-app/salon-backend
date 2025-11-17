import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta
from api.models import Style, Appointment


@pytest.fixture
def style():
    return Style.objects.create(
        name="Twists",
        category="braids",
        price_min=80,
        price_max=200,
        duration_mins=120,
    )


@pytest.fixture
def user():
    return User.objects.create_user(
        username="john",
        password="pass123",
        email="john@example.com",
        first_name="John",
        last_name="Doe"
    )


@pytest.mark.django_db
def test_appointment_create_guest(style):
    client = APIClient()
    res = client.post("/api/appointments/", {
        "style": style.id,
        "datetime": timezone.now().isoformat(),
        "contact_name": "Guest",
        "contact_email": "guest@example.com",
    })

    assert res.status_code == 201
    assert Appointment.objects.count() == 1


@pytest.mark.django_db
def test_appointment_create_user(style, user):
    client = APIClient()
    client.force_authenticate(user=user)

    res = client.post("/api/appointments/", {
        "style": style.id,
        "datetime": timezone.now().isoformat(),
        "contact_name": "",
        "contact_email": "",
    })

    assert res.status_code == 201
    appt = Appointment.objects.first()
    assert appt.user == user
    assert appt.contact_name == "John Doe"
    assert appt.contact_email == "john@example.com"


@pytest.mark.django_db
def test_appointment_list_user_can_only_see_theirs(style, user):
    user2 = User.objects.create_user(username="other", password="123")

    dt = timezone.now()
    Appointment.objects.create(user=user, style=style, datetime=dt)
    Appointment.objects.create(user=user2, style=style, datetime=dt + timedelta(hours=1))

    client = APIClient()
    client.force_authenticate(user=user)

    res = client.get("/api/appointments/")
    assert len(res.data) == 1


@pytest.mark.django_db
def test_appointment_taken_action(style):
    dt = timezone.now().replace(hour=10, minute=0)

    Appointment.objects.create(
        style=style,
        datetime=dt,
        contact_name="Guest",
        contact_email="x@example.com"
    )

    client = APIClient()
    date_str = dt.date().isoformat()

    res = client.get(f"/api/appointments/taken/?date={date_str}")

    assert res.status_code == 200
    assert res.data["taken"] == ["10:00"]


@pytest.mark.django_db
def test_appointment_upcoming(style, user):
    future = timezone.now() + timedelta(days=1)
    past = timezone.now() - timedelta(days=1)

    Appointment.objects.create(user=user, style=style, datetime=future)
    Appointment.objects.create(user=user, style=style, datetime=past)

    client = APIClient()
    client.force_authenticate(user=user)

    res = client.get("/api/appointments/upcoming/")

    assert len(res.data) == 1
    assert res.data[0]["datetime"].startswith(str(future.date()))


@pytest.mark.django_db
def test_appointment_cancel(style, user):
    appt = Appointment.objects.create(
        user=user,
        style=style,
        datetime=timezone.now() + timedelta(days=1)
    )

    client = APIClient()
    client.force_authenticate(user=user)

    res = client.post(f"/api/appointments/{appt.id}/cancel/")

    assert res.status_code == 200
    appt.refresh_from_db()
    assert appt.status == "cancelled"
