import pytest
from django.contrib.auth.models import User
from api.models import Profile
from api.serializers import UserProfileSerializer

@pytest.mark.django_db
def test_user_profile_serializer_reads_fields():
    user = User.objects.create_user(
        username="john",
        email="john@example.com",
        first_name="John",
        last_name="Doe",
    )
    profile = user.profile
    profile.phone_number = "555-5555"
    profile.preferred_stylist = "Maria"
    profile.save()

    serializer = UserProfileSerializer(user)
    assert serializer.data["phone"] == "555-5555"
    assert serializer.data["preferred_stylist"] == "Maria"
    assert serializer.data["email"] == "john@example.com"


@pytest.mark.django_db
def test_user_profile_serializer_updates_nested_fields():
    user = User.objects.create_user(username="sam", email="sam@example.com")

    data = {
        "first_name": "Samuel",
        "last_name": "Jackson",
        "dob": "1990-01-01",
        "phone": "12345",
        "preferred_stylist": "Kelly"
    }

    serializer = UserProfileSerializer(user, data=data, partial=True)
    assert serializer.is_valid(), serializer.errors
    serializer.save()

    user.refresh_from_db()
    profile = user.profile

    assert user.first_name == "Samuel"
    assert user.last_name == "Jackson"
    assert str(profile.dob) == "1990-01-01"
    assert profile.phone_number == "12345"
    assert profile.preferred_stylist == "Kelly"
