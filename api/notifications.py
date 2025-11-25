import requests
from django.template.loader import render_to_string
from django.utils.timezone import localtime
from django.conf import settings

MAILGUN_API_KEY = settings.MAILGUN_API_KEY
MAILGUN_DOMAIN = settings.MAILGUN_DOMAIN
MAILGUN_SENDER = settings.MAILGUN_SENDER


def mailgun_send(to, subject, html):
    """
    Send an email via Mailgun HTTP API.
    """
    if not to:
        return

    try:
        requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": MAILGUN_SENDER,
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=10,
        )
    except Exception:
        # Silent fail — prevents crashing the booking flow
        pass


def send_booking_confirmation_email(appt):
    """Send the standard appointment confirmation email."""
    to = appt.contact_email or (appt.user.email if appt.user else None)
    if not to:
        return

    dt_local = localtime(appt.datetime).strftime("%B %d, %Y at %I:%M %p")

    html = render_to_string("booking_confirmation.html", {
        "name": appt.contact_name or "there",
        "style_name": appt.style.name,
        "datetime": dt_local,
    })

    mailgun_send(
        to,
        f"Booking Confirmed — {appt.style.name}",
        html
    )
