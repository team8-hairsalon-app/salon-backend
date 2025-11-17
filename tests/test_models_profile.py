import pytest
from django.contrib.auth.models import User
from api.models import Profile

@pytest.mark.django_db
def test_profile_auto_created():
    user = User.objects.create_user(username="john", password="pass123")
    assert Profile.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_profile_not_duplicated_on_update():
    user = User.objects.create_user(username="jane", password="pass123")
    Profile.objects.get(user=user)

    user.username = "jane_new"
    user.save()

    assert Profile.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_profile_str():
    user = User.objects.create_user(username="tester", password="pass123")
    profile = user.profile
    assert str(profile) == f"Profile({user.id})"
