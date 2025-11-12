# api/models.py
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

class Style(models.Model):
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=50)  # braids, cut, color, styling, etc.
    price_min = models.DecimalField(max_digits=8, decimal_places=2)
    price_max = models.DecimalField(max_digits=8, decimal_places=2)
    duration_mins = models.PositiveIntegerField()
    image_url = models.URLField(blank=True)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)

    def __str__(self):
        return self.name


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("paid", "Paid"),  # optional
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
    )
    style = models.ForeignKey(Style, on_delete=models.PROTECT, related_name="appointments")
    datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)

    # guest/signed-in contact snapshot
    contact_name = models.CharField(max_length=120, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=40, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Prevent duplicate for signed-in users (same user+style+datetime)
            models.UniqueConstraint(
                fields=["user", "style", "datetime"],
                name="unique_user_style_when_datetime",
                condition=Q(user__isnull=False),
            ),
            # Prevent duplicate for guests by email (same email+style+datetime)
            models.UniqueConstraint(
                fields=["contact_email", "style", "datetime"],
                name="unique_guest_email_style_when_datetime",
                condition=Q(user__isnull=True) & ~Q(contact_email="") & Q(contact_email__isnull=False),
            ),
        ]

    def __str__(self):
        who = self.user or self.contact_name or "Guest"
        return f"{who} - {self.style} @ {self.datetime}"


class Profile(models.Model):
    """
    Extra, editable fields for each user that your Profile page shows.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    dob = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=40, blank=True, default="")
    preferred_stylist = models.CharField(max_length=120, blank=True, default="")

    def __str__(self):
        return f"Profile({self.user_id})"


@receiver(post_save, sender=User)
def _create_profile_on_user_create(sender, instance, created, **kwargs):
    # get_or_create avoids race conditions and duplicate creation
    if created:
        Profile.objects.get_or_create(user=instance)