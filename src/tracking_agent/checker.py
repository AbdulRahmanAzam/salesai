from __future__ import annotations

import email as email_lib
import email.header
import imaplib
import re
from datetime import datetime, timezone
from typing import Any

from tracking_agent.config import TrackingSettings
from tracking_agent.models import Response


class ResponseChecker:
    """
    Checks an IMAP mailbox for replies to sent outreach messages.

    Matches replies by:
    1. In-Reply-To / References headers matching outreach Message-IDs
    2. Subject line matching (Re: <original subject>)
    3. Sender email matching known contacts
    """

    def __init__(self, settings: TrackingSettings):
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(
            self.settings.imap_host
            and self.settings.imap_username
            and self.settings.imap_password
        )

    def check_responses(
        self,
        sent_messages: list[dict[str, Any]],
        since_date: str | None = None,
    ) -> list[Response]:
        """
        Check IMAP for replies to sent outreach messages.

        Args:
            sent_messages: List of sent message dicts with keys:
                message_id, contact_email, contact_name, contact_company, subject, id
            since_date: Only check emails since this date (IMAP format: "01-Jan-2026")

        Returns:
            List of Response objects for discovered replies.
        """
        if not self.is_configured():
            print("[warn] IMAP not configured. Cannot check for responses.")
            return []

        # Build lookup indexes
        message_id_index: dict[str, dict] = {}
        email_index: dict[str, dict] = {}
        subject_index: dict[str, dict] = {}
        for msg in sent_messages:
            if msg.get("message_id"):
                message_id_index[msg["message_id"]] = msg
            if msg.get("contact_email"):
                email_index[msg["contact_email"].lower()] = msg
            if msg.get("subject"):
                clean = _clean_subject(msg["subject"]).lower()
                subject_index[clean] = msg

        responses: list[Response] = []

        try:
            conn = self._connect()
            conn.select(self.settings.imap_folder, readonly=True)

            # Build IMAP search criteria
            criteria = "ALL"
            if since_date:
                criteria = f'(SINCE "{since_date}")'

            status, msg_nums = conn.search(None, criteria)
            if status != "OK" or not msg_nums[0]:
                conn.logout()
                return []

            msg_ids = msg_nums[0].split()
            print(f"[info] Checking {len(msg_ids)} emails in {self.settings.imap_folder}...")

            for msg_id in msg_ids:
                try:
                    status, data = conn.fetch(msg_id, "(RFC822)")
                    if status != "OK" or not data or not data[0]:
                        continue

                    raw = data[0]
                    if isinstance(raw, tuple) and len(raw) > 1:
                        raw_email = raw[1]
                    else:
                        continue

                    parsed = email_lib.message_from_bytes(raw_email)

                    # Try to match this email to a sent outreach message
                    match = _match_email(
                        parsed, message_id_index, email_index, subject_index
                    )
                    if match:
                        response = _build_response(parsed, match)
                        responses.append(response)

                except Exception as exc:
                    print(f"  [warn] Failed to process email {msg_id}: {exc}")
                    continue

            conn.logout()

        except imaplib.IMAP4.error as exc:
            print(f"[error] IMAP error: {exc}")
        except OSError as exc:
            print(f"[error] Connection error: {exc}")

        print(f"[info] Found {len(responses)} responses to outreach messages")
        return responses

    def _connect(self) -> imaplib.IMAP4_SSL | imaplib.IMAP4:
        if self.settings.imap_use_ssl:
            conn = imaplib.IMAP4_SSL(
                self.settings.imap_host, self.settings.imap_port
            )
        else:
            conn = imaplib.IMAP4(
                self.settings.imap_host, self.settings.imap_port
            )
        conn.login(self.settings.imap_username, self.settings.imap_password)
        return conn


def _match_email(
    parsed_email: email_lib.message.Message,
    message_id_index: dict[str, dict],
    email_index: dict[str, dict],
    subject_index: dict[str, dict],
) -> dict | None:
    """Try to match an IMAP email to a sent outreach message."""

    # Method 1: In-Reply-To header
    in_reply_to = parsed_email.get("In-Reply-To", "")
    if in_reply_to and in_reply_to in message_id_index:
        return message_id_index[in_reply_to]

    # Method 2: References header
    references = parsed_email.get("References", "")
    for ref in references.split():
        ref = ref.strip()
        if ref in message_id_index:
            return message_id_index[ref]

    # Method 3: From address + subject matching
    from_addr = _extract_email_address(parsed_email.get("From", ""))
    subject = _decode_header(parsed_email.get("Subject", ""))
    clean_subj = _clean_subject(subject).lower()

    if from_addr and from_addr.lower() in email_index:
        matched = email_index[from_addr.lower()]
        # Verify subject similarity — require it to avoid false positives
        orig_subj = _clean_subject(matched.get("subject", "")).lower()
        if orig_subj and (orig_subj in clean_subj or clean_subj in orig_subj):
            return matched
        # Without subject match, only match if email is unique to one outreach
        email_lower = from_addr.lower()
        matches_for_email = [m for m in email_index.values() if m.get("contact_email", "").lower() == email_lower]
        if len(matches_for_email) == 1:
            return matched

    # Method 4: Subject-only matching — DISABLED due to high false positive rate
    # A subject like "Re: Quick question" could match any outreach with that subject

    return None


def _build_response(
    parsed_email: email_lib.message.Message,
    matched_message: dict,
) -> Response:
    """Build a Response object from a parsed email and its matching outreach message."""
    from_addr = _extract_email_address(parsed_email.get("From", ""))
    subject = _decode_header(parsed_email.get("Subject", ""))
    date_str = parsed_email.get("Date", "")
    body = _extract_body(parsed_email)

    received_at = _parse_date(date_str) or datetime.now(timezone.utc).isoformat()

    return Response(
        outreach_message_id=matched_message.get("id", ""),
        contact_name=matched_message.get("contact_name", ""),
        contact_company=matched_message.get("contact_company", ""),
        contact_email=from_addr or "",
        subject=subject,
        body=body,
        received_at=received_at,
    )


def _extract_email_address(from_header: str) -> str | None:
    """Extract email address from a From header like 'Name <email@example.com>'."""
    match = re.search(r"<([^>]+)>", from_header)
    if match:
        return match.group(1)
    if "@" in from_header:
        return from_header.strip()
    return None


def _decode_header(value: str) -> str:
    """Decode an email header (handles encoded-word syntax)."""
    if not value:
        return ""
    parts = email.header.decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _extract_body(parsed_email: email_lib.message.Message) -> str:
    """Extract plain text body from an email message."""
    if parsed_email.is_multipart():
        for part in parsed_email.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fall back to HTML if no plain text
        for part in parsed_email.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    html = payload.decode(charset, errors="replace")
                    return _strip_html(html)
    else:
        payload = parsed_email.get_payload(decode=True)
        if payload:
            charset = parsed_email.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def _strip_html(html: str) -> str:
    """Simple HTML tag stripper."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    return text.strip()


def _clean_subject(subject: str) -> str:
    """Remove Re:, Fwd:, etc. from subject line."""
    return re.sub(r"^(?:re|fwd|fw)\s*:\s*", "", subject, flags=re.IGNORECASE).strip()


def _parse_date(date_str: str) -> str | None:
    """Parse email date to ISO format."""
    if not date_str:
        return None
    try:
        parsed = email_lib.utils.parsedate_to_datetime(date_str)
        return parsed.isoformat()
    except (TypeError, ValueError):
        return None
