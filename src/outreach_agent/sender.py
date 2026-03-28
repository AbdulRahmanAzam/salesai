from __future__ import annotations

import email.utils
import smtplib
import ssl
import time
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from outreach_agent.config import OutreachSettings


class EmailSender:
    """Production-grade SMTP email sender with TLS, rate limiting, and error handling."""

    def __init__(self, settings: OutreachSettings):
        self.settings = settings
        self._sends_today = 0
        self._last_send_time: float = 0

    def is_configured(self) -> bool:
        """Check if SMTP credentials are available."""
        return bool(
            self.settings.smtp_host
            and self.settings.smtp_username
            and self.settings.smtp_password
            and self.settings.sender_email
        )

    def send(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
    ) -> tuple[bool, str, str | None]:
        """
        Send a single email via SMTP.

        Returns:
            (success, message_id, error_message)
        """
        if not self.is_configured():
            return False, "", "SMTP not configured"

        if self._sends_today >= self.settings.daily_send_limit:
            return False, "", f"Daily send limit ({self.settings.daily_send_limit}) reached"

        # Rate limiting
        elapsed = time.monotonic() - self._last_send_time
        if elapsed < self.settings.send_delay_seconds:
            time.sleep(self.settings.send_delay_seconds - elapsed)

        message_id = f"<{uuid.uuid4().hex}@{self.settings.smtp_host}>"

        msg = MIMEMultipart("alternative")
        msg["From"] = email.utils.formataddr(
            (self.settings.sender_name, self.settings.sender_email)
        )
        msg["To"] = email.utils.formataddr((to_name, to_email))
        msg["Subject"] = subject
        msg["Message-ID"] = message_id
        msg["X-Mailer"] = "SalesIntelligence-OutreachAgent/1.0"

        # Plain text body
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # HTML version with minimal formatting
        html_body = _plain_to_html(body)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if self.settings.smtp_use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(
                    self.settings.smtp_host, self.settings.smtp_port, timeout=30
                ) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(
                        self.settings.smtp_username, self.settings.smtp_password
                    )
                    server.send_message(msg)
            else:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.settings.smtp_host, self.settings.smtp_port,
                    context=context, timeout=30
                ) as server:
                    server.login(
                        self.settings.smtp_username, self.settings.smtp_password
                    )
                    server.send_message(msg)

            self._sends_today += 1
            self._last_send_time = time.monotonic()
            return True, message_id, None

        except smtplib.SMTPAuthenticationError:
            return False, message_id, "SMTP authentication failed -- check credentials"
        except smtplib.SMTPRecipientsRefused:
            return False, message_id, f"Recipient refused: {to_email}"
        except smtplib.SMTPException as exc:
            return False, message_id, f"SMTP error: {exc}"
        except OSError as exc:
            return False, message_id, f"Connection error: {exc}"

    def send_batch(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Send multiple emails with rate limiting.

        Each message dict must have: to_email, to_name, subject, body, id
        Returns list of result dicts with: id, success, message_id, error
        """
        results = []
        for msg in messages:
            success, msg_id, error = self.send(
                to_email=msg["to_email"],
                to_name=msg["to_name"],
                subject=msg["subject"],
                body=msg["body"],
            )
            results.append({
                "id": msg.get("id"),
                "success": success,
                "message_id": msg_id,
                "error": error,
                "sent_at": datetime.now(timezone.utc).isoformat() if success else None,
            })
            if not success and "Daily send limit" in (error or ""):
                # Stop batch if limit reached
                for remaining in messages[len(results):]:
                    results.append({
                        "id": remaining.get("id"),
                        "success": False,
                        "message_id": "",
                        "error": "Batch halted: daily send limit reached",
                        "sent_at": None,
                    })
                break
        return results


def _plain_to_html(text: str) -> str:
    """Convert plain text to simple HTML email body."""
    import html as html_module

    escaped = html_module.escape(text)
    paragraphs = escaped.split("\n\n")
    html_parts = []
    for p in paragraphs:
        lines = p.replace("\n", "<br>")
        html_parts.append(f"<p style='margin: 0 0 12px 0; line-height: 1.5;'>{lines}</p>")
    return (
        "<div style='font-family: -apple-system, BlinkMacSystemFont, sans-serif; "
        "font-size: 14px; color: #1a1a2e; max-width: 600px;'>"
        + "".join(html_parts)
        + "</div>"
    )
