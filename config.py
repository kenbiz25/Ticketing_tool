import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-2024")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///database.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "static", "screenshots"
    )
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "doc", "docx", "xls", "xlsx", "txt", "csv"}
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
    API_KEY = os.getenv("API_KEY", "change-api-key-in-prod")

    # WhatsApp — Meta Cloud API
    WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN", "my_verify_token")
    WA_ACCESS_TOKEN = os.getenv("WA_ACCESS_TOKEN")          # Bearer token
    WA_PHONE_NUMBER_ID = os.getenv("WA_PHONE_NUMBER_ID")   # From Meta dashboard

    # WhatsApp — Twilio (alternative)
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WA_FROM = os.getenv("TWILIO_WA_FROM", "whatsapp:+14155238886")

    # Email inbound — IMAP polling
    IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
    IMAP_USER = os.getenv("IMAP_USER")
    IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
    IMAP_MAILBOX = os.getenv("IMAP_MAILBOX", "INBOX")
    IMAP_POLL_KEY = os.getenv("IMAP_POLL_KEY", "change-imap-key-in-prod")

    # WhatsApp provider: "meta" or "twilio"
    WA_PROVIDER = os.getenv("WA_PROVIDER", "meta")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "change-telegram-secret")

    # Slack
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")         # Incoming Webhook URL
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")   # For verifying slash commands

    # Microsoft Teams
    TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")         # Incoming Webhook connector URL

    # Translation (Google Cloud Translation API)
    TRANSLATE_API_KEY = os.getenv("TRANSLATE_API_KEY")
    TRANSLATE_PROVIDER = os.getenv("TRANSLATE_PROVIDER", "google")  # google | libretranslate
    LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL", "http://localhost:5000")

    # WhatsApp Cloud API
    WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
    WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "medtronic_verify")

    # Widget
    WIDGET_ALLOWED_ORIGINS = os.environ.get("WIDGET_ALLOWED_ORIGINS", "*")
