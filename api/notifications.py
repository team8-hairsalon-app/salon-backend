# api/notifications.py
from django.core.mail import send_mail
from django.conf import settings

def _send_email(to_email: str, subject: str, message: str):
    if not to_email:
        return
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=True,
        )
    except Exception:
        pass

def _send_sms(to_number: str, body: str):
    sid = getattr(settings, "TWILIO_SID", "")
    token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
    from_num = getattr(settings, "TWILIO_PHONE_NUMBER", "")
    if not (sid and token and from_num and to_number):
        return
    try:
        from twilio.rest import Client
        Client(sid, token).messages.create(
            to=to_number,
            from_=from_num,
            body=body,
        )
    except Exception:
        pass

def send_booking_confirmation(appt):
    """
    Email/SMS right after an appointment is created.
    Slots are enforced, so we confirm immediately.
    """
    service = getattr(appt.style, "name", "Service")
    dt = appt.datetime.strftime("%Y-%m-%d %H:%M")
    name = appt.contact_name or "there"

    subject = "Your Hair Salon appointment is confirmed"
    message = (
        f"Hi {name},\n\n"
        f"Your appointment for {service} on {dt} is confirmed.\n"
        f"If anything changes before your appointment, we’ll notify you in advance.\n\n"
        f"Please do not reply to this email. For assistance, contact the salon using the phone or email listed on our website.\n\n"
        f"— Hair Salon"
    )

    _send_email(appt.contact_email or "", subject, message)
    _send_sms(appt.contact_phone or "", message)

def send_payment_confirmation(appt, amount: float):
    """
    Email acknowledgement when Stripe marks the appointment as paid.
    """
    service = getattr(appt.style, "name", "Service")
    dt = appt.datetime.strftime("%Y-%m-%d %H:%M")
    name = appt.contact_name or "there"
    amt = f"${amount:,.2f}"

    subject = "Payment received – Hair Salon"
    message = (
        f"Hi {name},\n\n"
        f"Thank you for your payment of {amt} for {service}. "
        f"Your appointment on {dt} has been successfully confirmed.\n"
        f"If anything changes before your appointment, we’ll notify you in advance.\n\n"
        f"Please do not reply to this email. For assistance, contact the salon using the phone number or email listed on our website.\n\n"
        f"— Hair Salon"
    )
    _send_email(appt.contact_email or "", subject, message)