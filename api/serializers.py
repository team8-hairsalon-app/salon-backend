# api/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Style, Appointment, Profile

# ---------- Register ----------
class RegisterSerializer(serializers.ModelSerializer):
    """
    Create a Django user. Email is unique; if username isn't provided,
    default username = email.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()
    username = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "first_name", "last_name")

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "An account with this email already exists.", code="unique"
            )
        return email

    def create(self, validated_data):
        username = validated_data.get("username") or validated_data["email"]
        email = validated_data["email"].strip().lower()
        first_name = validated_data.get("first_name", "")
        last_name = validated_data.get("last_name", "")
        password = validated_data.pop("password")

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save()
        return user

# ---------- Profile (current user) ----------
class UserProfileSerializer(serializers.ModelSerializer):
    """
    Exposes extra fields on the related Profile.
    Frontend fields:
      - dob                <-> profile.dob
      - phone              <-> profile.phone_number
      - preferred_stylist  <-> profile.preferred_stylist
    Email is read-only here.
    """
    dob = serializers.DateField(source="profile.dob", required=False, allow_null=True)
    phone = serializers.CharField(source="profile.phone_number", required=False, allow_blank=True)
    preferred_stylist = serializers.CharField(
        source="profile.preferred_stylist", required=False, allow_blank=True
    )

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email", "dob", "phone", "preferred_stylist")
        read_only_fields = ("email",)

    def update(self, instance, validated_data):
        # Pull nested profile data if present
        profile_data = validated_data.pop("profile", {})

        # Update simple user fields
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.save(update_fields=["first_name", "last_name"])

        # Ensure profile exists and update it
        profile, _ = Profile.objects.get_or_create(user=instance)

        if "dob" in profile_data:
            profile.dob = profile_data.get("dob")
        if "phone_number" in profile_data:
            profile.phone_number = profile_data.get("phone_number", "")
        if "preferred_stylist" in profile_data:
            profile.preferred_stylist = profile_data.get("preferred_stylist", "")
        profile.save()

        return instance

# ---------- Styles ----------
class StyleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Style
        fields = "__all__"

# ---------- Appointments ----------
class AppointmentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    style_name = serializers.CharField(source="style.name", read_only=True)

    # Extra fields so the UI can render the badge & price correctly
    is_paid = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    style_price_min = serializers.DecimalField(
        source="style.price_min", max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = Appointment
        fields = (
            "id",
            "user",
            "user_email",
            "style",
            "style_name",
            "datetime",
            "status",
            "notes",
            "contact_name",
            "contact_email",
            "contact_phone",
            "created_at",
            # extra
            "is_paid",
            "amount",
            "style_price_min",
        )
        read_only_fields = ("status", "created_at", "user")

    def get_is_paid(self, obj):
        """
        True if the appointment has a boolean is_paid flag set OR
        if the textual status is 'paid'.
        """
        try:
            if getattr(obj, "is_paid", False):
                return True
        except Exception:
            pass
        return str(getattr(obj, "status", "")).lower() == "paid"

    def get_amount(self, obj):
        """
        Return appointment.amount if your model has it; otherwise fall back
        to the style's minimum price so the UI can always show a number.
        """
        # Appointment-level amount (if present on your model)
        if hasattr(obj, "amount") and getattr(obj, "amount") is not None:
            return obj.amount
        # Fallback to style price_min
        style = getattr(obj, "style", None)
        return getattr(style, "price_min", None)

    def validate(self, attrs):
        """
        Validation rules:
        - Name is required for everyone.
        - Guests must provide at least one contact method (email or phone).
        - Signed-in users: auto-fill name/email if missing.
        - Normalize email to lowercase/trim so DB uniqueness works reliably.
        """
        request = self.context.get("request")
        user = getattr(request, "user", None)

        name = (attrs.get("contact_name") or "").strip()
        email = (attrs.get("contact_email") or "").strip().lower()
        phone = (attrs.get("contact_phone") or "").strip()

        # Normalize back ('' -> None) so conditional unique constraints work
        attrs["contact_email"] = email or None

        # Auto-fill for signed-in users (snapshot)
        if user and getattr(user, "is_authenticated", False):
            if not name:
                name = (f"{user.first_name} {user.last_name}").strip() or user.username
                attrs["contact_name"] = name
            if not email and user.email:
                attrs["contact_email"] = user.email.strip().lower()

        if not name:
            raise serializers.ValidationError({"contact_name": "Please provide your name."})

        if not (attrs.get("contact_email") or phone):
            raise serializers.ValidationError({
                "contact_email": "Provide at least one contact method (email or phone).",
                "contact_phone": "Provide at least one contact method (email or phone).",
            })

        return attrs