import pytest
from rest_framework.test import APIClient
from api.models import Style


@pytest.mark.django_db
def test_style_list():
    Style.objects.create(name="Cut", category="cut", price_min=10, price_max=20, duration_mins=30)
    
    client = APIClient()
    res = client.get("/api/styles/")

    assert res.status_code == 200
    assert len(res.data) == 1


@pytest.mark.django_db
def test_style_create():
    client = APIClient()
    res = client.post("/api/styles/", {
        "name": "Braids",
        "category": "braids",
        "price_min": 50,
        "price_max": 100,
        "duration_mins": 120,
    })

    assert res.status_code == 201
    assert Style.objects.count() == 1
