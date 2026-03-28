from __future__ import annotations

import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid

from tracking_agent.config import TrackingSettings


class FollowUpSender:
    """Send follow-up emails via SMTP. Shares config pattern with outreach sender."""

    def __init__(self, settings: TrackingSettings):
        self.settings = settings
        self._sent_today = 0

    def is_configured(self) -> bool:
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
    ) -> tuple[bool, str | None, str | None]:
        """
        Send a follow-up email.

        Returns:
            (success, message_id, error)
        """
        if not self.is_configured():
            return False, None, "SMTP not configured"

        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr((self.settings.sender_name, self.settings.sender_email))
        msg["To"] = formataddr((to_name, to_email))
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid(domain=self.settings.sender_email.split("@")[-1])

        msg.attach(MIMEText(body, "plain", "utf-8"))
        html_body = _plain_to_html(body)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if self.settings.smtp_use_tls:
                server = smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port)

            server.login(self.settings.smtp_username, self.settings.smtp_password)
            server.sendmail(self.settings.sender_email, [to_email], msg.as_string())
            server.quit()

            self._sent_today += 1
            time.sleep(2)  # basic rate limiting
            return True, msg["Message-ID"], None

        except smtplib.SMTPException as exc:
            return False, None, str(exc)
        except OSError as exc:
            return False, None, str(exc)


def _plain_to_html(text: str) -> str:
    """Convert plain text to simple HTML."""
    import html

    escaped = html.escape(text)
    paragraphs = escaped.split("\n\n")
    html_parts = [f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs]
    return (
        '<!DOCTYPE html><html><body style="font-family:sans-serif;'
        'font-size:14px;color:#333;line-height:1.6">'
        + "".join(html_parts)
        + "</body></html>"
    )
