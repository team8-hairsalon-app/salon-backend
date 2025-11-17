import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from api.models import Profile


@pytest.mark.django_db
def test_me_profile_retrieve():
    user = User.objects.create_user(username="sam", password="pass123", email="sam@example.com")
    client = APIClient()
    client.force_authenticate(user=user)

    res = client.get("/api/me/profile/")
    assert res.status_code == 200
    assert res.data["email"] == "sam@example.com"


@pytest.mark.django_db
def test_me_profile_update():
    user = User.objects.create_user(username="sam", password="pass123", email="sam@example.com")
    client = APIClient()
    client.force_authenticate(user=user)

    res = client.patch("/api/me/profile/", {
        "first_name": "Samuel",
        "phone": "555-5555"
    })

    assert res.status_code == 200

    user.refresh_from_db()
    assert user.first_name == "Samuel"
    assert user.profile.phone_number == "555-5555"
