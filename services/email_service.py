"""Production-ready email notification service for CareCircle.

Architecture note
-----------------
EmailService is responsible only for SMTP delivery. It knows nothing about
caregiver business logic; that lives in NotificationService. This separation
makes it straightforward to add future channels (SMS, Teams, etc.) without
touching delivery code.
"""

from __future__ import annotations

import logging
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTML email templates
# ---------------------------------------------------------------------------

_BASE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{subject}</title>
  <style>
    body {{ margin: 0; padding: 0; background: #f4f6f8; font-family: Arial, sans-serif; }}
    .wrapper {{ max-width: 600px; margin: 32px auto; background: #ffffff;
                border-radius: 8px; overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
    .header {{ background: #2e7d6b; padding: 28px 32px; text-align: center; }}
    .header h1 {{ margin: 0; color: #ffffff; font-size: 22px; letter-spacing: 0.5px; }}
    .header p  {{ margin: 4px 0 0; color: #a8d5cc; font-size: 13px; }}
    .badge {{ display: inline-block; background: #e8f5f2; color: #2e7d6b;
              font-size: 12px; font-weight: bold; padding: 4px 12px;
              border-radius: 12px; margin: 20px 32px 0; }}
    .body {{ padding: 24px 32px 8px; }}
    .body h2 {{ margin: 0 0 12px; color: #1a1a2e; font-size: 18px; }}
    .body p  {{ margin: 0 0 12px; color: #444; font-size: 15px; line-height: 1.6; }}
    .detail-box {{ background: #f0faf7; border-left: 4px solid #2e7d6b;
                   border-radius: 0 6px 6px 0; padding: 14px 18px; margin: 16px 0; }}
    .detail-box p {{ margin: 0; color: #2e7d6b; font-size: 14px; }}
    .cta {{ text-align: center; padding: 24px 32px; }}
    .cta a {{ background: #2e7d6b; color: #ffffff; text-decoration: none;
              padding: 12px 28px; border-radius: 6px; font-size: 15px;
              font-weight: bold; display: inline-block; }}
    .footer {{ background: #f4f6f8; text-align: center; padding: 16px 32px;
               color: #999; font-size: 12px; border-top: 1px solid #e0e0e0; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>CareCircle</h1>
      <p>Care Management System</p>
    </div>
    <div class="badge">{badge}</div>
    <div class="body">
      <h2>{heading}</h2>
      {body_html}
    </div>
    <div class="cta">
      <a href="{app_url}">Open CareCircle</a>
    </div>
    <div class="footer">
      This is an automated notification from CareCircle. Do not reply to this email.
    </div>
  </div>
</body>
</html>
"""


def _render_html(
    subject: str,
    badge: str,
    heading: str,
    body_html: str,
    app_url: str,
) -> str:
    return _BASE_HTML.format(
        subject=subject,
        badge=badge,
        heading=heading,
        body_html=body_html,
        app_url=app_url,
    )


def birthday_html(caregiver: dict[str, Any], app_url: str) -> tuple[str, str]:
    """Return (html, plain_text) for a birthday reminder."""
    name = caregiver.get("name", "the caregiver")
    birthday = caregiver.get("birthday", "")
    body_html = f"""\
      <p>Today is <strong>{name}'s birthday</strong>.</p>
      <div class="detail-box">
        <p>🎂 <strong>Date of Birth:</strong> {birthday}</p>
      </div>
      <p>Please remember to wish {name} a happy birthday and update the
         interaction record after contacting them.</p>
    """
    plain = (
        f"CareCircle – Birthday Reminder\n\n"
        f"Today is {name}'s birthday ({birthday}).\n\n"
        f"Please remember to wish them a happy birthday and update the "
        f"interaction record.\n\n{app_url}"
    )
    return _render_html(
        subject=f"🎂 Caregiver Birthday Reminder – {name}",
        badge="Birthday Reminder",
        heading=f"Today is {name}'s Birthday",
        body_html=body_html,
        app_url=app_url,
    ), plain


def grant_followup_html(caregiver: dict[str, Any], app_url: str) -> tuple[str, str]:
    """Return (html, plain_text) for a grant follow-up reminder."""
    name = caregiver.get("name", "the caregiver")
    due = caregiver.get("check_when", "")
    what = caregiver.get("check_what", "")
    body_html = f"""\
      <p>A grant follow-up is required for <strong>{name}</strong>.</p>
      <div class="detail-box">
        <p>📋 <strong>Due Date:</strong> {due}</p>
        {"<p>📝 <strong>Notes:</strong> " + what + "</p>" if what else ""}
      </div>
      <p>Please review the caregiver's grant status and complete the required
         follow-up action as soon as possible.</p>
    """
    plain = (
        f"CareCircle – Grant Follow-up Required\n\n"
        f"A grant follow-up is required for {name}.\n"
        f"Due: {due}\n"
        + (f"Notes: {what}\n" if what else "")
        + f"\n{app_url}"
    )
    return _render_html(
        subject=f"📋 Grant Follow-up Required – {name}",
        badge="Grant Follow-up",
        heading=f"Grant Follow-up Required – {name}",
        body_html=body_html,
        app_url=app_url,
    ), plain


def checkin_html(caregiver: dict[str, Any], app_url: str) -> tuple[str, str]:
    """Return (html, plain_text) for a monthly check-in reminder."""
    name = caregiver.get("name", "the caregiver")
    due = caregiver.get("check_when", "")
    what = caregiver.get("check_what", "")
    body_html = f"""\
      <p>A monthly check-in is overdue for <strong>{name}</strong>.</p>
      <div class="detail-box">
        <p>📞 <strong>Due Date:</strong> {due}</p>
        {"<p>📝 <strong>Notes:</strong> " + what + "</p>" if what else ""}
      </div>
      <p>Please contact {name} to conduct the monthly check-in and update
         the record accordingly.</p>
    """
    plain = (
        f"CareCircle – Monthly Check-in Reminder\n\n"
        f"A monthly check-in is overdue for {name}.\n"
        f"Due: {due}\n"
        + (f"Notes: {what}\n" if what else "")
        + f"\n{app_url}"
    )
    return _render_html(
        subject=f"📞 Monthly Caregiver Check-in Reminder – {name}",
        badge="Monthly Check-in",
        heading=f"Monthly Check-in Overdue – {name}",
        body_html=body_html,
        app_url=app_url,
    ), plain


def grant_check_html(caregiver: dict[str, Any], message: str, app_url: str) -> tuple[str, str]:
    """Return (html, plain_text) for a grant check-date alert."""
    name = caregiver.get("name", "the caregiver")
    body_html = f"""\
      <p>A grant check date has been triggered for <strong>{name}</strong>.</p>
      <div class="detail-box">
        <p>📋 {message}</p>
      </div>
      <p>Please review the caregiver's grant details and take the required action.</p>
    """
    plain = (
        f"CareCircle – Grant Check Alert\n\n"
        f"Grant check for {name}: {message}\n\n{app_url}"
    )
    return _render_html(
        subject=f"📋 Grant Follow-up Required – {name}",
        badge="Grant Check",
        heading=f"Grant Check – {name}",
        body_html=body_html,
        app_url=app_url,
    ), plain


def test_html(app_url: str) -> tuple[str, str]:
    """Return (html, plain_text) for a connectivity test email."""
    body_html = """\
      <p>This is a test email from CareCircle to confirm that your email
         notification service is configured correctly.</p>
      <div class="detail-box">
        <p>✅ SMTP connection established and authentication successful.</p>
      </div>
      <p>No action is required. Your email alerts are ready to go.</p>
    """
    plain = (
        "CareCircle – Test Email\n\n"
        "This is a test email confirming your SMTP configuration is working.\n\n"
        f"{app_url}"
    )
    return _render_html(
        subject="✅ CareCircle Email Test",
        badge="System Test",
        heading="Email Service is Working",
        body_html=body_html,
        app_url=app_url,
    ), plain


# ---------------------------------------------------------------------------
# EmailService
# ---------------------------------------------------------------------------

class EmailService:
    """SMTP delivery service.

    Designed to be channel-agnostic at the boundary: NotificationService
    calls ``send_*`` methods; this class handles all SMTP concerns.
    """

    MAX_RETRIES = 2
    RETRY_DELAY = 2  # seconds between retries

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
        use_tls: bool = True,
        use_ssl: bool = False,
        app_url: str = "http://127.0.0.1:5000",
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self._password = password  # never logged
        self.sender = sender
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.app_url = app_url

    # ------------------------------------------------------------------
    # Connection check
    # ------------------------------------------------------------------

    def check_connection(self) -> bool:
        """Return True if SMTP credentials can be verified; log and return False otherwise."""
        try:
            with self._connect() as conn:
                logger.info("✓ Email service connected successfully (host=%s port=%s)", self.host, self.port)
                return True
        except smtplib.SMTPAuthenticationError:
            logger.warning("⚠ Email service unavailable — authentication failed (host=%s)", self.host)
        except smtplib.SMTPConnectError as exc:
            logger.warning("⚠ Email service unavailable — connection error: %s", exc)
        except TimeoutError:
            logger.warning("⚠ Email service unavailable — SMTP timeout (host=%s port=%s)", self.host, self.port)
        except Exception as exc:
            logger.warning("⚠ Email service unavailable — %s: %s", type(exc).__name__, exc)
        return False

    # ------------------------------------------------------------------
    # Core send
    # ------------------------------------------------------------------

    def send(
        self,
        to: str | list[str],
        subject: str,
        html: str,
        text: str | None = None,
    ) -> bool:
        """Send an email with HTML body and optional plain-text fallback.

        Returns True on success, False on failure. Never raises.
        """
        recipients = [to] if isinstance(to, str) else list(to)
        if not recipients:
            logger.warning("Email send skipped — no recipients provided")
            return False

        msg = self._build_message(recipients, subject, html, text)
        return self._send_with_retry(recipients, msg)

    # ------------------------------------------------------------------
    # Alert-type helpers
    # ------------------------------------------------------------------

    def send_birthday_alert(self, caregiver: dict, recipients: list[str]) -> bool:
        name = caregiver.get("name", "the caregiver")
        html, text = birthday_html(caregiver, self.app_url)
        subject = f"🎂 Caregiver Birthday Reminder – {name}"
        logger.info("Email queued: birthday alert for caregiver id=%s to %s", caregiver.get("id"), recipients)
        return self.send(recipients, subject, html, text)

    def send_grant_followup_alert(self, caregiver: dict, recipients: list[str]) -> bool:
        name = caregiver.get("name", "the caregiver")
        html, text = grant_followup_html(caregiver, self.app_url)
        subject = f"📋 Grant Follow-up Required – {name}"
        logger.info("Email queued: grant follow-up alert for caregiver id=%s", caregiver.get("id"))
        return self.send(recipients, subject, html, text)

    def send_checkin_alert(self, caregiver: dict, recipients: list[str]) -> bool:
        name = caregiver.get("name", "the caregiver")
        html, text = checkin_html(caregiver, self.app_url)
        subject = f"📞 Monthly Caregiver Check-in Reminder – {name}"
        logger.info("Email queued: check-in alert for caregiver id=%s", caregiver.get("id"))
        return self.send(recipients, subject, html, text)

    def send_grant_check_alert(self, caregiver: dict, message: str, recipients: list[str]) -> bool:
        name = caregiver.get("name", "the caregiver")
        html, text = grant_check_html(caregiver, message, self.app_url)
        subject = f"📋 Grant Follow-up Required – {name}"
        logger.info("Email queued: grant check alert for caregiver id=%s", caregiver.get("id"))
        return self.send(recipients, subject, html, text)

    def send_test_email(self, recipient: str) -> bool:
        html, text = test_html(self.app_url)
        logger.info("Email queued: test email to %s", recipient)
        return self.send(recipient, "✅ CareCircle Email Test", html, text)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> smtplib.SMTP | smtplib.SMTP_SSL:
        """Open and authenticate an SMTP connection."""
        if self.use_ssl:
            conn = smtplib.SMTP_SSL(self.host, self.port, timeout=15)
        else:
            conn = smtplib.SMTP(self.host, self.port, timeout=15)
            if self.use_tls:
                conn.ehlo()
                conn.starttls()
                conn.ehlo()
        logger.debug("Connection established to %s:%s", self.host, self.port)
        conn.login(self.username, self._password)
        logger.debug("Authentication successful for %s", self.username)
        return conn

    def _build_message(
        self,
        recipients: list[str],
        subject: str,
        html: str,
        text: str | None,
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(recipients)
        if text:
            msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        return msg

    def _send_with_retry(self, recipients: list[str], msg: MIMEMultipart) -> bool:
        last_exc: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 2):  # +1 for the initial try
            try:
                with self._connect() as conn:
                    conn.sendmail(self.sender, recipients, msg.as_string())
                logger.info("Email sent — subject=%r to=%s", msg["Subject"], recipients)
                return True
            except smtplib.SMTPAuthenticationError as exc:
                logger.error("Email failed — authentication error: %s", exc)
                return False  # no point retrying auth failures
            except smtplib.SMTPRecipientsRefused as exc:
                logger.error("Email failed — recipient(s) refused: %s", exc)
                return False
            except smtplib.SMTPException as exc:
                last_exc = exc
                logger.warning("Email attempt %d failed — %s: %s", attempt, type(exc).__name__, exc)
            except TimeoutError as exc:
                last_exc = exc
                logger.warning("Email attempt %d failed — SMTP timeout", attempt)
            except Exception as exc:
                last_exc = exc
                logger.warning("Email attempt %d failed — unexpected: %s: %s", attempt, type(exc).__name__, exc)

            if attempt <= self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY * attempt)

        logger.error("Email failed after %d attempt(s) — %s", self.MAX_RETRIES + 1, last_exc)
        return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def email_service_from_config(config: object) -> EmailService | None:
    """Build an EmailService from a Flask Config object.

    Returns None if SMTP is not configured (no host), so callers can guard:
        svc = email_service_from_config(Config)
        if svc:
            svc.send_birthday_alert(...)
    """
    host = getattr(config, "SMTP_HOST", None)
    username = getattr(config, "SMTP_USERNAME", None)
    password = getattr(config, "SMTP_PASSWORD", None)
    sender = getattr(config, "SMTP_FROM", None)

    if not all([host, username, password, sender]):
        return None

    return EmailService(
        host=host,
        port=getattr(config, "SMTP_PORT", 587),
        username=username,
        password=password,
        sender=sender,
        use_tls=getattr(config, "SMTP_USE_TLS", True),
        use_ssl=getattr(config, "SMTP_USE_SSL", False),
        app_url=getattr(config, "APP_BASE_URL", "http://127.0.0.1:5000"),
    )
