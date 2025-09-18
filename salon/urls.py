from django.urls import include, path

urlpatterns = [
    path("", include("salon.api.urls")),
]
