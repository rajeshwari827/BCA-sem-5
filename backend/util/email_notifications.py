"""SMTP email helpers for donation workflow notifications."""

import os
import smtplib
from email.message import EmailMessage


def send_email(to_address, subject, body):
    """Send one email using SMTP environment settings; return (sent, reason)."""
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    from_address = os.getenv("SMTP_FROM", username).strip()
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        return False, "SMTP_PORT must be a number"

    if not host or not from_address or not to_address:
        return False, "SMTP settings or recipient email are missing"

    try:
        message = EmailMessage()
        message["From"] = from_address
        message["To"] = to_address
        message["Subject"] = subject
        message.set_content(body)

        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as server:
                if username:
                    server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if username:
                    server.login(username, password)
                server.send_message(message)
        return True, None
    except Exception as error:
        return False, str(error)


def send_acceptance_emails(donation, donor, receiver):
    """Notify donor and receiver after a donation acceptance is committed."""
    donation_id = donation["donation_id"]
    food_name = donation["food_name"]
    quantity = donation["quantity"]
    donor_name = donor["resturaent_name"]
    donor_phone = donor.get("phone") or "Not provided"
    donor_address = donor.get("address") or "Not provided"
    receiver_name = receiver["organization_name"]
    representative = receiver["representative_name"]
    receiver_phone = receiver.get("phone") or "Not provided"
    receiver_id = receiver["ngo_id"]

    donor_body = (
        "Your food donation has been accepted.\n\n"
        f"Donation ID: {donation_id}\n"
        f"Food: {food_name}\n"
        f"Quantity: {quantity}\n"
        f"Receiver organization: {receiver_name}\n"
        f"Representative: {representative}\n"
        f"Receiver ID: {receiver_id}\n"
        f"Receiver phone: {receiver_phone}\n\n"
        "Please contact the receiver to coordinate pickup."
    )
    receiver_body = (
        "Your food donation acceptance is confirmed.\n\n"
        f"Donation ID: {donation_id}\n"
        f"Food: {food_name}\n"
        f"Quantity: {quantity}\n"
        f"Donor restaurant: {donor_name}\n"
        f"Donor phone: {donor_phone}\n"
        f"Pickup address: {donor_address}\n\n"
        "Please contact the donor to coordinate pickup."
    )

    results = {}
    for key, address, subject, body in (
        ("donor", donor.get("email"), f"Your donation #{donation_id} was accepted", donor_body),
        ("receiver", receiver.get("email"), f"Acceptance confirmed for donation #{donation_id}", receiver_body),
    ):
        sent, reason = send_email(address, subject, body)
        results[key] = {"sent": sent}
        if not sent:
            results[key]["reason"] = reason
    return results
