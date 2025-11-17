import pytest
import stripe
from django.conf import settings
from unittest.mock import patch
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from api.models import Style, Appointment
from django.utils import timezone


@pytest.mark.django_db
@patch("api.views.stripe.checkout.Session.create")
def test_create_checkout_session(mock_create):
    settings.STRIPE_SECRET_KEY = "dummy"
    stripe.api_key = "dummy"

    user = User.objects.create_user(username="sam", password="pass123", email="sam@example.com")
    style = Style.objects.create(name="Cut", category="cut", price_min=20, price_max=40, duration_mins=30)
    appt = Appointment.objects.create(user=user, style=style, datetime=timezone.now())

    mock_create.return_value.url = "https://test-session-url"

    client = APIClient()
    client.force_authenticate(user=user)

    res = client.post(f"/api/checkout/create-session/{appt.id}/")

    assert res.status_code == 200
    assert res.json()["url"] == "https://test-session-url"
    assert mock_create.called


@pytest.mark.django_db
@patch("api.views.stripe.Webhook.construct_event")
def test_stripe_webhook_marks_as_paid(mock_construct):
    settings.STRIPE_WEBHOOK_SECRET = "dummy_secret"

    style = Style.objects.create(name="Cut", category="cut", price_min=20, price_max=40, duration_mins=30)
    appt = Appointment.objects.create(style=style, datetime=timezone.now())

    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"appointment_id": appt.id}, "amount_total": 5000}}
    }

    mock_construct.return_value = event

    client = APIClient()
    res = client.post("/api/webhooks/stripe/", content_type="application/json")

    assert res.status_code == 200
    appt.refresh_from_db()
    assert appt.status == "paid"
