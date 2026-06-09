"""
Multi-channel ticket intake:
  - WhatsApp via Meta Cloud API  (POST /integrations/whatsapp)
  - WhatsApp via Twilio          (POST /integrations/whatsapp/twilio)
  - Email inbound webhook        (POST /integrations/email-inbound)
  - Email IMAP poll              (GET  /integrations/email-poll?key=IMAP_POLL_KEY)
"""
import imaplib
import email as email_lib
from email.header import decode_header
import re
import json
import hashlib
from datetime import datetime

import requests
from flask import Blueprint, request, jsonify, current_app

from models import db, Ticket, IssueCategory, WhatsAppSession, Country, SLAPolicy, CSATRating, TelegramSession
from utils import log_history, notify_staff, create_notification, translate_text

integrations = Blueprint("integrations", __name__, url_prefix="/integrations")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_ticket_from_data(data: dict, channel: str, external_id: str = None) -> Ticket:
    """Create and flush a Ticket from normalised dict. Caller must commit."""
    ticket = Ticket(
        sl_no=Ticket.generate_sl_no(),
        channel=channel,
        external_id=external_id,
        issue_reporter_name=data.get("name", ""),
        issue_reporter_contact=data.get("phone", ""),
        form_submit_email=data.get("email", ""),
        district=data.get("district", ""),
        upazila=data.get("upazila", ""),
        issue_type=data.get("issue_type", "General"),
        problem_details=data.get("details", ""),
        priority=data.get("priority", "Medium"),
        current_status="Open",
    )
    db.session.add(ticket)
    db.session.flush()

    # Apply SLA
    sla = SLAPolicy.query.filter_by(priority=ticket.priority, is_active=True).first()
    if sla:
        from datetime import timedelta
        ticket.due_date = datetime.utcnow() + timedelta(hours=sla.resolution_hours)

    # CSAT placeholder
    db.session.add(CSATRating(ticket_id=ticket.id))

    log_history(ticket.id, None, f"Ticket created via {channel}")
    notify_staff(
        f"[{channel.upper()}] New ticket {ticket.sl_no}: {ticket.issue_type} — {ticket.district}",
        ticket_id=ticket.id,
        notif_type="info",
    )
    return ticket


# ── WhatsApp — Meta Cloud API ──────────────────────────────────────────────────

WA_STATES = {
    "INIT": "Hi! 👋 I'm the Support Bot. I'll help you log a support ticket.\n\nReply with your *name*:",
    "WAITING_NAME": "Got it! Now please share your *location* (district or area):",
    "WAITING_LOCATION": "Thanks! Briefly describe *what issue* you're facing:",
    "WAITING_ISSUE": "Almost done! Any more *details* (error messages, steps to reproduce)?",
    "WAITING_DETAILS": None,  # handled in code
}

RESET_WORDS = {"reset", "start over", "restart", "new ticket", "hi", "hello"}


def _wa_send_meta(phone: str, message: str):
    """Send a WhatsApp message via Meta Cloud API."""
    token = current_app.config.get("WA_ACCESS_TOKEN")
    phone_id = current_app.config.get("WA_PHONE_NUMBER_ID")
    if not token or not phone_id:
        current_app.logger.warning("Meta WhatsApp not configured — skip send.")
        return
    try:
        requests.post(
            f"https://graph.facebook.com/v19.0/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message},
            },
            timeout=10,
        )
    except Exception as e:
        current_app.logger.error(f"WhatsApp send error: {e}")


def _wa_send_twilio(phone: str, message: str):
    """Send a WhatsApp message via Twilio."""
    sid = current_app.config.get("TWILIO_ACCOUNT_SID")
    token = current_app.config.get("TWILIO_AUTH_TOKEN")
    from_number = current_app.config.get("TWILIO_WA_FROM")
    if not sid or not token:
        current_app.logger.warning("Twilio not configured — skip send.")
        return
    try:
        requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={
                "From": from_number,
                "To": f"whatsapp:{phone}" if not phone.startswith("whatsapp:") else phone,
                "Body": message,
            },
            timeout=10,
        )
    except Exception as e:
        current_app.logger.error(f"Twilio send error: {e}")


def _wa_send(phone: str, message: str):
    provider = current_app.config.get("WA_PROVIDER", "meta")
    if provider == "twilio":
        _wa_send_twilio(phone, message)
    else:
        _wa_send_meta(phone, message)


def _wa_handle_message(phone: str, text: str):
    """State-machine conversation handler. Returns response text."""
    text = text.strip()

    session = WhatsAppSession.query.get(phone)
    if not session:
        session = WhatsAppSession(phone=phone, state="INIT", data={})
        db.session.add(session)

    if text.lower() in RESET_WORDS:
        session.state = "INIT"
        session.data = {}
        db.session.commit()
        return WA_STATES["INIT"]

    state = session.state

    if state == "INIT":
        session.state = "WAITING_NAME"
        db.session.commit()
        return WA_STATES["INIT"]

    if state == "WAITING_NAME":
        session.data = {**session.data, "name": text}
        session.state = "WAITING_LOCATION"
        db.session.commit()
        return WA_STATES["WAITING_NAME"]

    if state == "WAITING_LOCATION":
        session.data = {**session.data, "district": text}
        session.state = "WAITING_ISSUE"
        db.session.commit()
        return WA_STATES["WAITING_LOCATION"]

    if state == "WAITING_ISSUE":
        session.data = {**session.data, "issue_type": text}
        session.state = "WAITING_DETAILS"
        db.session.commit()
        return WA_STATES["WAITING_ISSUE"]

    if state == "WAITING_DETAILS":
        data = {**session.data, "details": text, "phone": phone}
        ticket = _make_ticket_from_data(data, channel="whatsapp", external_id=f"wa_{phone}_{int(datetime.utcnow().timestamp())}")
        db.session.commit()
        session.state = "INIT"
        session.data = {}
        db.session.commit()
        return (
            f"✅ Your ticket *{ticket.sl_no}* has been logged!\n\n"
            f"Issue: {data.get('issue_type')}\n"
            f"We'll get back to you shortly. Type 'new ticket' to log another."
        )

    # Fallback
    session.state = "INIT"
    session.data = {}
    db.session.commit()
    return WA_STATES["INIT"]


@integrations.route("/whatsapp", methods=["GET", "POST"])
def whatsapp_meta():
    """Meta Cloud API webhook."""
    if request.method == "GET":
        # Webhook verification
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == current_app.config.get("WA_VERIFY_TOKEN"):
            return challenge, 200
        return "Forbidden", 403

    data = request.get_json(silent=True) or {}
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                messages = change.get("value", {}).get("messages", [])
                for msg in messages:
                    phone = msg.get("from")
                    text = msg.get("text", {}).get("body", "")
                    if phone and text:
                        reply = _wa_handle_message(phone, text)
                        _wa_send_meta(phone, reply)
    except Exception as e:
        current_app.logger.error(f"WhatsApp webhook error: {e}")
    return jsonify({"status": "ok"}), 200


@integrations.route("/whatsapp/twilio", methods=["POST"])
def whatsapp_twilio():
    """Twilio WhatsApp webhook (TwiML or status callback)."""
    phone = request.form.get("From", "").replace("whatsapp:", "")
    text = request.form.get("Body", "")
    if phone and text:
        try:
            reply = _wa_handle_message(phone, text)
            _wa_send_twilio(phone, reply)
        except Exception as e:
            current_app.logger.error(f"Twilio webhook error: {e}")
    return "", 204


# ── Email Inbound — Webhook (SendGrid / Mailgun / Postmark) ───────────────────

def _parse_email_body(text_body: str, html_body: str = "") -> dict:
    """Extract ticket fields from email body (plain or HTML)."""
    body = text_body or re.sub(r"<[^>]+>", " ", html_body)
    body = re.sub(r"\s+", " ", body).strip()
    return {
        "details": body[:2000],
        "priority": "High" if re.search(r"\b(urgent|critical|asap|immediately)\b", body, re.I) else "Medium",
    }


def _create_ticket_from_email(sender: str, subject: str, body: str,
                               external_id: str, html_body: str = "") -> Ticket | None:
    # Deduplicate
    if Ticket.query.filter_by(external_id=external_id).first():
        return None
    parsed = _parse_email_body(body, html_body)
    name_match = re.match(r"^([^<]+)", sender)
    name = name_match.group(1).strip().strip('"') if name_match else sender
    email_match = re.search(r"<([^>]+)>", sender)
    email_addr = email_match.group(1) if email_match else sender

    data = {
        "name": name or email_addr,
        "email": email_addr,
        "issue_type": subject[:100],
        **parsed,
    }
    ticket = _make_ticket_from_data(data, channel="email", external_id=external_id)
    return ticket


@integrations.route("/email-inbound", methods=["POST"])
def email_inbound_webhook():
    """
    Handles inbound emails from:
    - SendGrid: JSON with 'from', 'subject', 'text', 'html', 'headers'
    - Mailgun:  form-encoded with 'From', 'subject', 'body-plain', 'body-html', 'Message-Id'
    - Postmark: JSON with 'From', 'Subject', 'TextBody', 'HtmlBody', 'MessageID'
    """
    ct = request.content_type or ""
    if "json" in ct:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    # Normalise across providers
    sender = (data.get("from") or data.get("From") or "").strip()
    subject = (data.get("subject") or data.get("Subject") or "(No Subject)").strip()
    body = (data.get("text") or data.get("body-plain") or data.get("TextBody") or "").strip()
    html = (data.get("html") or data.get("body-html") or data.get("HtmlBody") or "").strip()
    msg_id = (data.get("headers", {}).get("Message-Id", "") if isinstance(data.get("headers"), dict)
              else data.get("Message-Id") or data.get("MessageID") or "").strip()

    if not sender:
        return jsonify({"error": "No sender"}), 400

    ext_id = hashlib.sha256((msg_id or f"{sender}{subject}{body[:100]}").encode()).hexdigest()[:40]

    try:
        ticket = _create_ticket_from_email(sender, subject, body, ext_id, html)
        if ticket:
            db.session.commit()
            return jsonify({"status": "created", "sl_no": ticket.sl_no}), 201
        return jsonify({"status": "duplicate"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Email inbound error: {e}")
        return jsonify({"error": str(e)}), 500


# ── Email IMAP Polling ─────────────────────────────────────────────────────────

def _decode_mime_header(value: str) -> str:
    parts = decode_header(value)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _get_email_body(msg) -> tuple[str, str]:
    plain, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            payload = part.get_payload(decode=True)
            if payload:
                charset = part.get_content_charset("utf-8") or "utf-8"
                if ctype == "text/plain":
                    plain = payload.decode(charset, errors="replace")
                elif ctype == "text/html":
                    html = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset("utf-8") or "utf-8"
            if msg.get_content_type() == "text/html":
                html = payload.decode(charset, errors="replace")
            else:
                plain = payload.decode(charset, errors="replace")
    return plain, html


@integrations.route("/email-poll")
def email_poll():
    """Poll IMAP inbox and create tickets from unseen emails. Secured by IMAP_POLL_KEY."""
    key = request.args.get("key", "")
    if key != current_app.config.get("IMAP_POLL_KEY"):
        return jsonify({"error": "Unauthorized"}), 401

    host = current_app.config.get("IMAP_HOST")
    port = current_app.config.get("IMAP_PORT", 993)
    user = current_app.config.get("IMAP_USER")
    password = current_app.config.get("IMAP_PASSWORD")
    mailbox = current_app.config.get("IMAP_MAILBOX", "INBOX")

    if not host or not user or not password:
        return jsonify({"error": "IMAP not configured"}), 503

    created, skipped = 0, 0
    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(user, password)
        mail.select(mailbox)
        _, msg_ids = mail.search(None, "UNSEEN")
        for mid in (msg_ids[0].split() if msg_ids[0] else []):
            _, data = mail.fetch(mid, "(RFC822)")
            raw = data[0][1]
            msg = email_lib.message_from_bytes(raw)
            sender = _decode_mime_header(msg.get("From", ""))
            subject = _decode_mime_header(msg.get("Subject", "(No Subject)"))
            msg_id = msg.get("Message-ID", "")
            plain, html = _get_email_body(msg)
            ext_id = hashlib.sha256((msg_id or f"{sender}{subject}").encode()).hexdigest()[:40]
            ticket = _create_ticket_from_email(sender, subject, plain, ext_id, html)
            if ticket:
                mail.store(mid, "+FLAGS", "\\Seen")
                created += 1
            else:
                skipped += 1
        mail.logout()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"IMAP poll error: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"created": created, "skipped": skipped}), 200


# ── Enhanced REST API ──────────────────────────────────────────────────────────

@integrations.route("/api/subcategories")
def api_subcategories():
    """Return subcategories for a given category (for cascading JS)."""
    cat_id = request.args.get("category_id", type=int)
    if not cat_id:
        return jsonify([])
    from models import IssueSubcategory
    subs = IssueSubcategory.query.filter_by(category_id=cat_id, is_active=True).order_by(IssueSubcategory.display_order).all()
    return jsonify([{"id": s.id, "name": s.name} for s in subs])


@integrations.route("/api/admin-units")
def api_admin_units():
    """Cascading admin unit lookup."""
    level = request.args.get("level", type=int)
    parent_id = request.args.get("parent_id", type=int)
    country_id = request.args.get("country_id", type=int)

    if level == 1 and country_id:
        from models import AdminLevel1
        units = AdminLevel1.query.filter_by(country_id=country_id).order_by(AdminLevel1.name).all()
    elif level == 2 and parent_id:
        from models import AdminLevel2
        units = AdminLevel2.query.filter_by(level1_id=parent_id).order_by(AdminLevel2.name).all()
    elif level == 3 and parent_id:
        from models import AdminLevel3
        units = AdminLevel3.query.filter_by(level2_id=parent_id).order_by(AdminLevel3.name).all()
    else:
        return jsonify([])

    return jsonify([{"id": u.id, "name": u.name} for u in units])


# ── Telegram Bot ───────────────────────────────────────────────────────────────

TG_STATES = {
    "INIT": "👋 Hi! I'm the Support Bot.\n\nPlease reply with your *name*:",
    "WAITING_NAME": "Thanks! Now share your *location* (district/area):",
    "WAITING_LOCATION": "Got it! Briefly describe *the issue* you're facing:",
    "WAITING_ISSUE": "Almost done! Any *extra details* (error messages, steps)?",
}

RESET_TG = {"reset", "start", "/start", "hi", "hello", "new ticket"}


def _tg_send(chat_id: str, text: str):
    token = current_app.config.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        current_app.logger.error(f"Telegram send error: {e}")


def _tg_handle(chat_id: str, username: str, text: str):
    session = TelegramSession.query.get(str(chat_id))
    if not session:
        session = TelegramSession(chat_id=str(chat_id), username=username, state="INIT")
        db.session.add(session)
        db.session.flush()

    text = (text or "").strip()
    if text.lower() in RESET_TG:
        session.state = "INIT"
        session.data = {}
        db.session.commit()
        _tg_send(chat_id, TG_STATES["INIT"])
        return

    state = session.state

    if state == "INIT":
        session.state = "WAITING_NAME"
        db.session.commit()
        _tg_send(chat_id, TG_STATES["INIT"])

    elif state == "WAITING_NAME":
        session.data = {**session.data, "name": text}
        session.state = "WAITING_LOCATION"
        db.session.commit()
        _tg_send(chat_id, TG_STATES["WAITING_NAME"])

    elif state == "WAITING_LOCATION":
        session.data = {**session.data, "district": text}
        session.state = "WAITING_ISSUE"
        db.session.commit()
        _tg_send(chat_id, TG_STATES["WAITING_LOCATION"])

    elif state == "WAITING_ISSUE":
        session.data = {**session.data, "issue_type": text}
        session.state = "WAITING_DETAILS"
        db.session.commit()
        _tg_send(chat_id, TG_STATES["WAITING_ISSUE"])

    elif state == "WAITING_DETAILS":
        data = {**session.data, "details": text, "phone": f"tg:{chat_id}"}
        ticket = _make_ticket_from_data(data, "telegram", external_id=f"tg_{chat_id}")
        session.state = "INIT"
        session.data = {}
        db.session.commit()
        _tg_send(
            chat_id,
            f"✅ Ticket *{ticket.sl_no}* created!\n\n"
            f"Issue: {data.get('issue_type', '')}\n"
            f"We'll follow up shortly. Reply *reset* to raise a new ticket.",
        )


@integrations.route("/integrations/telegram/webhook", methods=["POST"])
def telegram_webhook():
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != current_app.config.get("TELEGRAM_WEBHOOK_SECRET", ""):
        return jsonify({"error": "Forbidden"}), 403

    data = request.json or {}
    message = data.get("message") or data.get("edited_message") or {}
    if not message:
        return jsonify({"ok": True})

    chat_id = str(message.get("chat", {}).get("id", ""))
    username = message.get("from", {}).get("username") or message.get("from", {}).get("first_name", "")
    text = message.get("text", "")

    if not chat_id:
        return jsonify({"ok": True})

    try:
        _tg_handle(chat_id, username, text)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Telegram handler error: {e}")

    return jsonify({"ok": True})


# ── Translation API ────────────────────────────────────────────────────────────

@integrations.route("/api/translate", methods=["POST"])
def api_translate():
    """
    POST body: { "text": "...", "target": "fr", "source": "auto" }
    Returns:   { "translated": "..." }
    """
    from flask_login import current_user
    if not current_user.is_authenticated:
        return jsonify({"error": "Login required"}), 401
    data = request.json or {}
    text = data.get("text", "").strip()
    target = data.get("target", "en").strip()
    source = data.get("source", "auto").strip()
    if not text or not target:
        return jsonify({"error": "text and target are required"}), 400
    result = translate_text(text, target, source)
    return jsonify({"translated": result})
