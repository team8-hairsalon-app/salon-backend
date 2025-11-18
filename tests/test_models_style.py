import pytest
from api.models import Style

@pytest.mark.django_db
def test_style_str():
    style = Style.objects.create(
        name="Box Braids",
        category="braids",
        price_min=100,
        price_max=300,
        duration_mins=180,
    )
    assert str(style) == "Box Braids"
