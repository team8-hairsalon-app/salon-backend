from django.db import models
from .base_model import BaseModel

class Appointment(BaseModel):
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="appointments"
    )
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    style_id = models.IntegerField()
    style_name = models.CharField(max_length=100)
    appointment_time = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("canceled", "Canceled"),
        ],
    )
