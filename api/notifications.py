from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.timezone import localtime
from django.conf import settings


def send_booking_confirmation_email(appt):
    """Send HTML booking confirmation email."""

    to = appt.contact_email or None
    if not to:
        return

    dt_local = localtime(appt.datetime).strftime("%B %d, %Y at %I:%M %p")

    context = {
        "name": appt.contact_name or "there",
        "style_name": appt.style.name,
        "datetime": dt_local,
    }

    subject = f"Booking Confirmed — {appt.style.name}"

    try:
        html_body = render_to_string("booking_confirmation.html", context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=True)

    except Exception as e:
        raise
