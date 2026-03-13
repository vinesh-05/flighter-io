import os
import base64
import requests


def send_ticket_email(to_email: str, pdf_path: str):
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")

    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY not configured")

    with open(pdf_path, "rb") as f:
        pdf_base64 = base64.b64encode(f.read()).decode()

    payload = {
        "sender": {
            "name": "Flighter AI",
            "email": "ai.flighter.io@gmail.com"  # can be any verified sender
        },
        "to": [
            {"email": to_email}
        ],
        "subject": "Your Flight Ticket",
        "htmlContent": """
            <p>Your booking is confirmed.</p>
            <p>Your flight ticket is attached.</p>
            <p>Thank you for choosing Flighter ✈️</p>
        """,
        "attachment": [
            {
                "content": pdf_base64,
                "name": "flight_ticket.pdf"
            }
        ]
    }

    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers=headers,
        json=payload,
        timeout=10,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Brevo email failed: {response.status_code} {response.text}"
        )

def send_password_reset_email(to_email: str, reset_link: str):

    BREVO_API_KEY = os.getenv("BREVO_API_KEY")

    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY not configured")

    payload = {
        "sender": {
            "name": "Flighter AI",
            "email": "ai.flighter.io@gmail.com"
        },
        "to": [
            {"email": to_email}
        ],
        "subject": "Reset your Flighter password",
        "htmlContent": f"""
            <p>Hello,</p>

            <p>We received a request to reset your password.</p>

            <p>
                <a href="{reset_link}">
                    Click here to reset your password
                </a>
            </p>

            <p>This link expires in <b>15 minutes</b>.</p>

            <p>If you didn't request this, please ignore this email.</p>

            <p>— Flighter ✈️</p>
        """
    }

    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers=headers,
        json=payload,
        timeout=10,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Brevo email failed: {response.status_code} {response.text}"
        )