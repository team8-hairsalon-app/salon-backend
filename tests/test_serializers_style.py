import pytest
from api.models import Style
from api.serializers import StyleSerializer

@pytest.mark.django_db
def test_style_serializer_full_cycle():
    style = Style.objects.create(
        name="Braids",
        category="braids",
        price_min=50,
        price_max=120,
        duration_mins=90,
    )

    serializer = StyleSerializer(style)
    data = serializer.data

    assert data["name"] == "Braids"
    assert data["price_min"] == "50.00"
    assert data["price_max"] == "120.00"
