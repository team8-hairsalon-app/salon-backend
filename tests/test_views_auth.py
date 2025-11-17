import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_register_view_creates_user():
    client = APIClient()

    res = client.post("/api/auth/register/", {
        "email": "test@example.com",
        "password": "mypassword123",
        "first_name": "John",
        "last_name": "Doe",
    })

    assert res.status_code == 201
    assert User.objects.filter(email="test@example.com").exists()


@pytest.mark.django_db
def test_token_obtain_allows_login_with_email_instead_of_username():
    User.objects.create_user(
        username="john123",
        email="john@example.com",
        password="xyz123456",
        first_name="John",
        last_name="Doe"
    )

    client = APIClient()
    res = client.post("/api/auth/login/", {
        "username": "john@example.com",
        "password": "xyz123456"
    })

    assert res.status_code == 200
    assert "access" in res.data
    assert "refresh" in res.data
