import pytest
from django.contrib.auth.models import User
from api.serializers import RegisterSerializer

@pytest.mark.django_db
def test_register_serializer_creates_user():
    data = {
        "email": "Test@Email.com",
        "password": "mypassword123",
        "first_name": "John",
        "last_name": "Doe",
        "username": ""
    }

    serializer = RegisterSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    user = serializer.save()

    assert user.email == "test@email.com"
    assert user.username == "test@email.com"
    assert user.check_password("mypassword123") is True
    assert user.first_name == "John"
    assert user.last_name == "Doe"


@pytest.mark.django_db
def test_register_serializer_rejects_duplicate_email():
    User.objects.create_user(
        username="existing", email="taken@example.com", password="pass"
    )

    serializer = RegisterSerializer(data={
        "email": "taken@example.com",
        "password": "mypassword123"
    })
    assert not serializer.is_valid()
    assert "email" in serializer.errors
    assert serializer.errors["email"][0].code == "unique"
