# Medtronic LABS — Support Ticketing System

A multi-channel, intelligent support platform built for Medtronic LABS field operations across 8 countries (Kenya, Bangladesh, India, Bhutan, Sierra Leone, Tanzania, Rwanda, Saudi Arabia). Supports ticket intake via web form, WhatsApp conversational bot, embeddable in-app widget, email, and REST API — with proactive nudges, CSAT tracking, and country-specific escalation flows.

---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Getting Started](#getting-started)
4. [Environment Variables](#environment-variables)
5. [Project Structure](#project-structure)
6. [Default Credentials](#default-credentials)
7. [Roles & Permissions](#roles--permissions)
8. [SLA Policies](#sla-policies)
9. [Country Escalation Matrices](#country-escalation-matrices)
10. [Channels & Integrations](#channels--integrations)
11. [Intelligent Support Features](#intelligent-support-features)
12. [Feature Reference](#feature-reference)

---

## Features

### Ticket Management

- **Multi-channel intake** — web form, WhatsApp (conversational bot), embeddable widget, email, and REST API
- **Three ticket views** — List, Split (LinkedIn-style preview), and Kanban (Jira-style columns)
- **SLA tracking** — seven priority tiers (P1–P5, OTP, OUTAGE) with automatic breach detection and countdown timers
- **Status workflow** — Open → In Progress → Pending → Resolved → Closed → Reopened
- **Merge, duplicate, and link tickets** — parent/child hierarchy, related/blocks/duplicates link types
- **Custom fields** — admin-configurable text, dropdown, checkbox, date, number fields per ticket
- **Auto-assignment** — round-robin across active agents by open ticket count
- **Fixed sidebar** — always visible, toggleable, never moves with scroll

### Intelligent Support Layer

- **WhatsApp conversational bot** — 5-step guided ticket creation via any WhatsApp number; agents reply from the dashboard; status updates pushed back to the user
- **Embeddable in-app widget** — single `<script>` tag drops a floating support widget into SPICE, Tiberbu, or Afyangu; searches Knowledge Base articles first, falls back to ticket form with page context pre-filled
- **Proactive nudges** — automatic aging alerts for P1/P2 tickets with no agent response after 2 hours; CSAT surveys pushed to WhatsApp 1 hour after ticket resolution
- **Broadcast messaging** — admins send proactive WhatsApp messages to DSOs filtered by country and role
- **CSAT tracking** — 1–5 star ratings via WhatsApp reply, widget, or email link; agent leaderboard, 30-day trend chart, response rate analytics

### Communication

- **In-app notifications** — real-time bell with unread count; polling every 30 seconds
- **Telegram bot** — conversational ticket creation via webhook
- **Slack / Microsoft Teams** — outbound webhook notifications for critical tickets and SLA breaches
- **Real-time translation** — translate ticket descriptions via Google Translate or LibreTranslate
- **Call logging** — log inbound/outbound calls against tickets with duration, outcome, and notes

### Automation & Workflows

- **Visual rule builder** — if/then automation rules at `/admin/automation` with 7 condition fields and 8 action types
- **Trigger events** — ticket created, status changed, priority changed, reply received
- **Actions** — set priority/status, assign agent, add tag, escalate, add internal note, notify staff, send email to reporter
- **Background scheduler** — APScheduler runs aging checks every 30 min and CSAT dispatch every 60 min automatically

### Knowledge Base

- **Public help center** at `/kb/` — searchable homepage, category pages, article detail
- **Widget integration** — KB articles surface inside the embeddable widget before the ticket form
- **Article feedback** — "Was this helpful?" thumbs up/down (IP-deduplicated)
- **Admin management** — HTML article editor, category CRUD at `/admin/kb`

### Dashboards & Analytics

- **Role-aware dashboards** — Super Admin, Admin/DSO, Reporter, and Viewer (reports-only) views
- **Analytics dashboard** at `/admin/analytics` — date range (7/30/90/180 days/custom), volume chart, SLA compliance, channel/category breakdowns, agent performance table
- **Reports** at `/admin/reports` — status, priority, escalation pyramid (L1–L4), district, and platform charts
- **CSAT dashboard** at `/admin/csat` — average score, score distribution, 30-day trend, agent leaderboard, recent feedback
- **Export** — CSV and Excel with styled headers and colour-coding
- **WhatsApp Inbox** at `/admin/whatsapp` — all WhatsApp conversations, state per session, agent reply from dashboard

### UI/UX

- **Dark / Light mode** — Bootstrap 5.3 native, toggle in navbar, persisted in `localStorage` with no flash on load
- **Keyboard shortcuts** — `N` New Ticket, `I` Inbox, `D` Dashboard, `R` Reports, `/` focus search, `Alt+T` toggle theme, `?` help
- **Drag-and-drop attachments** — any file input wrapped in a `.drop-zone` div
- **Mobile-first** — responsive across all screen sizes; widget goes full-screen on mobile
- **Custom branding** — app name, logo, tagline, primary colour, nav background at `/admin/branding`

### Operations

- **Multi-level RBAC** — five roles with regional scoping (country / admin-level-1) via `UserRegionRole`
- **Collision detection** — 5-minute edit lock with warning banner
- **Time tracking** — log minutes worked per ticket with per-agent breakdowns
- **Saved views** — persist filter combinations as named views (private or shared)
- **Tags, canned responses, bulk actions, audit trail**
- **Ticket attachments** — viewable and downloadable by all levels with access

### Security & Compliance

- **Login audit log** — every login success/failure recorded with IP and user-agent at `/admin/audit-log`
- **Ticket change history** — full audit trail of all field changes
- **GDPR data export** — users download their data at `/account/gdpr-export`
- **Right to be forgotten** — admin anonymization of any user account
- **User preferences** — per-user timezone and display language at `/account/preferences`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.0 |
| ORM | Flask-SQLAlchemy + SQLite (dev) / PostgreSQL (prod) |
| Auth | Flask-Login + Werkzeug password hashing |
| Frontend | Jinja2 + Bootstrap 5.3 + Chart.js 4.4 + Font Awesome 6.4 |
| File uploads | Werkzeug + Pillow |
| Email | SMTP (smtplib) |
| Excel export | openpyxl |
| Timezones | pytz |
| Background jobs | APScheduler 3.10 (in-process, no Redis required) |
| WhatsApp | Meta Cloud API (Graph v18) |
| Widget | Vanilla JS, Shadow DOM, zero dependencies |

> **Production path**: Flask → FastAPI; SQLite → PostgreSQL; APScheduler → Celery + Redis for distributed workers.

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- pip

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd User_Support

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in the required values. At minimum set `SECRET_KEY`. Everything else has safe defaults for local development.

### 4. Run the application

```bash
# Development (auto-reload on file changes)
flask run --debug

# or
python -m flask run --debug
```

The app starts at **http://localhost:5000**.

On first run it automatically seeds:

- A default Super Admin account (`superadmin` / `Admin@123` — **change immediately**)
- Built-in SLA policies for all seven priority tiers (P1–P5, OTP, OUTAGE)
- Country and administrative location data for all 8 countries
- Issue taxonomy (6 categories, 23+ subcategories)
- Country escalation matrices for Kenya (3 streams), Bangladesh, and Sierra Leone

### 5. (Optional) Seed demo data

```bash
python seed_demo.py
```

Seeds 80 tickets, 200 comments, tags, canned responses, automation rules, and 12 KB articles for testing all features.

### 6. (Optional) Seed Kenya sub-county locations

```bash
python seed_kenya_locations.py
```

Seeds all 47 counties and 305 sub-counties for Kenya.

---

## Environment Variables

Copy `.env.example` to `.env`. Variables marked **required** must be set for that feature to work; others have working defaults.

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(insecure default)* | **Required** — Flask session signing key. Set to a long random string in production. |
| `DATABASE_URL` | `sqlite:///database.db` | SQLAlchemy connection URI. Use `postgresql://user:pass@host/db` for PostgreSQL. |

### Email / SMTP

| Variable | Default | Description |
|----------|---------|-------------|
| `MAIL_SERVER` | `smtp.gmail.com` | Outbound SMTP server |
| `MAIL_PORT` | `587` | SMTP port (TLS) |
| `MAIL_USERNAME` | — | SMTP username / sender address |
| `MAIL_PASSWORD` | — | SMTP password or app password |
| `ADMIN_EMAIL` | `admin@example.com` | Address that receives critical-ticket alerts |

### WhatsApp — Meta Cloud API

| Variable | Default | Description |
|----------|---------|-------------|
| `WHATSAPP_TOKEN` | — | Meta Cloud API permanent / system user token |
| `WHATSAPP_PHONE_ID` | — | Phone Number ID from Meta Business dashboard |
| `WHATSAPP_VERIFY_TOKEN` | `medtronic_verify` | Verification token entered when registering the webhook on Meta |

Register your webhook URL on Meta: `https://your-domain.com/webhooks/whatsapp`

### Embeddable Widget

| Variable | Default | Description |
|----------|---------|-------------|
| `WIDGET_ALLOWED_ORIGINS` | `*` | CORS allowed origins for the widget API. Set to your app domains in production (e.g. `https://spice.medtroniclabs.org`). |

### Telegram Bot

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Secret for validating Telegram webhook calls |

### Slack / Teams

| Variable | Description |
|----------|-------------|
| `SLACK_WEBHOOK_URL` | Incoming Webhook URL |
| `SLACK_SIGNING_SECRET` | For verifying Slash Command requests |
| `TEAMS_WEBHOOK_URL` | Microsoft Teams Incoming Webhook connector URL |

### Email Inbound (IMAP polling)

| Variable | Default | Description |
|----------|---------|-------------|
| `IMAP_HOST` | `imap.gmail.com` | IMAP server |
| `IMAP_PORT` | `993` | IMAP SSL port |
| `IMAP_USER` | — | IMAP login address |
| `IMAP_PASSWORD` | — | IMAP password or app password |
| `IMAP_MAILBOX` | `INBOX` | Mailbox folder to poll |

### Translation

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSLATE_API_KEY` | — | Google Cloud Translation API key |
| `TRANSLATE_PROVIDER` | `google` | `google` or `libretranslate` |

---

## Project Structure

```
User_Support/
├── app.py                    # Application factory, DB migrations, seeding, APScheduler
├── config.py                 # All configuration loaded from environment
├── models.py                 # SQLAlchemy models (26 models)
├── requirements.txt
├── .env.example
│
├── routes/
│   ├── auth.py               # Login, logout, register, preferences, GDPR export
│   ├── tickets.py            # Ticket CRUD, comments, SLA, CSV/Excel export, REST API
│   ├── dashboard.py          # Role-aware dashboards, analytics, reports, regional filter
│   ├── admin_tools.py        # Tags, canned responses, SLA, branding, escalation matrices
│   ├── webhooks.py           # WhatsApp Cloud API webhook + agent reply + inbox view
│   ├── widget_api.py         # CORS-enabled API for the embeddable support widget
│   ├── nudges.py             # Broadcasts, CSAT dashboard, nudge log, aging check
│   ├── automation.py         # Automation rules CRUD
│   ├── kb.py                 # Knowledge base (public + admin)
│   ├── notifications.py      # In-app notification inbox
│   └── integrations.py       # Email and Telegram intake webhooks
│
├── templates/
│   ├── base.html             # Shared layout: dark mode, shortcuts, fixed sidebar, widget
│   ├── portal/               # Reporter and DSO dashboards (list/split/kanban views)
│   ├── admin/
│   │   ├── analytics.html            # Full-filter analytics dashboard
│   │   ├── reports.html              # Reports + escalation pyramid
│   │   ├── sla.html                  # HMIS ITSM escalation matrix (P1–OUTAGE)
│   │   ├── whatsapp_inbox.html       # WhatsApp conversation view
│   │   ├── broadcasts.html           # Send / history of broadcast messages
│   │   ├── nudge_log.html            # Nudge delivery log
│   │   ├── csat_dashboard.html       # CSAT ratings, trend, agent leaderboard
│   │   ├── escalation_matrices.html  # Country escalation matrix list
│   │   ├── escalation_matrix_detail.html  # Per-country matrix (multi-stream for Kenya)
│   │   └── ...                       # Other admin pages
│   ├── kb/                   # Public knowledge base
│   └── account/              # User preferences
│
├── static/
│   ├── widget/
│   │   └── support-widget.js   # Self-contained embeddable widget (shadow DOM)
│   └── screenshots/            # Uploaded file attachments
│
├── seed_demo.py              # 80 tickets, 200 comments, KB articles, automation rules
├── seed_kenya_locations.py   # 47 counties + 305 sub-counties
└── run_seed.py               # Seeds country escalation matrices (KE 3-stream, BD, SL)
```

### Database Models

| Model | Purpose |
|-------|---------|
| `User` | Agents, admins, reporters, viewers — with timezone/language preferences |
| `UserRegionRole` | Multi-region, multi-role assignments (country / admin-level-1 scoping) |
| `Ticket` | Core ticket with SLA, channel, widget context, WhatsApp phone |
| `TicketComment` | Public and internal notes (WhatsApp messages prefixed `[WhatsApp]`) |
| `TicketHistory` | Immutable change audit trail |
| `TicketAttachment` | File uploads linked to tickets or comments |
| `TicketWatcher` | Users subscribed to ticket updates |
| `TicketLink` | Related / blocks / duplicates relationships |
| `Tag` / `ticket_tags` | Tagging system |
| `CannedResponse` | Pre-written reply templates |
| `SLAPolicy` | Per-priority response/resolution targets (P1–P5, OTP, OUTAGE) with L1–L4 hours |
| `CustomField` / `TicketFieldValue` | Admin-defined extra fields |
| `SavedView` | Named filter presets (private or shared) |
| `CSATRating` | Customer satisfaction scores with secure token for email/widget submission |
| `NudgeLog` | Record of every nudge sent (CSAT surveys, aging alerts, broadcasts) |
| `BroadcastMessage` | Outbound WhatsApp broadcasts with targeting metadata |
| `AutomationRule` | If/then workflow automation |
| `KBCategory` / `KBArticle` / `KBArticleFeedback` | Knowledge base |
| `BrandingSettings` | App name, logo, colours (singleton) |
| `LoginAuditLog` | Authentication event log (IP + user-agent) |
| `TimeEntry` | Time tracking per ticket |
| `CallLog` | Call logging against tickets |
| `Notification` | In-app notification inbox |
| `WhatsAppSession` | Conversation state machine per phone number |
| `TelegramSession` | Conversation state for Telegram bot |
| `CountryEscalationMatrix` | Per-country support flow (streams + shared levels JSON) |
| `Country` / `AdminLevel1–3` | 8-country location hierarchy with business hours |

---

## Default Credentials

| Username | Password | Role |
|----------|----------|------|
| `superadmin` | `Admin@123` | Super Admin |

> **Change the password immediately after first login.**  
> Go to your username dropdown → **Preferences**, or navigate to `/account/preferences`.

---

## Roles & Permissions

| Role | Submit Tickets | Update / Assign | Reports / Analytics | User Management | System Config |
|------|:-:|:-:|:-:|:-:|:-:|
| Super Admin | Yes | Yes | Yes | Yes | Yes |
| Admin | Yes | Yes | Yes | Yes (limited) | No |
| DSO | Yes | Yes | Yes (own region) | No | No |
| Reporter | Yes (own only) | No | No | No | No |
| Viewer | No | No | Yes (read-only) | No | No |

### Regional Scoping

Admins and DSOs see only tickets from countries/regions assigned to them via **Admin → Users → Manage Regions**. Super Admins bypass all regional filters. Users with no region configured retain global access as a safe fallback.

---

## SLA Policies

Based on the HMIS ITSM Escalation Matrix. Edit at **Admin → SLA Policies** (`/admin/sla`). Only Super Admins can edit.

| Code | Priority | First Response | L1 Resolution | Auto-Escalate | 24/7 |
|------|----------|:-:|:-:|:-:|:-:|
| P1 | Critical | 15 min | 1 hour | Yes → L3 | Yes |
| P2 | High | 1 hour | 4 hours | Yes → L2 | Yes |
| P3 | Medium | 4 hours | 1 business day | If L2 breaches | No |
| P4 | Low | 1 business day | 3 business days | No | No |
| P5 | Enhancement | 2 business days | Roadmap | No | No |
| OTP | OTP Failure | 15 min | L3 direct (2h) | Yes → L3 | Yes |
| OUTAGE | Full Outage | ~5 min | L4 direct (2h) | Yes → L4 | Yes |

Business hours are configured **per country** (timezone, work start/end, working days) for accurate SLA calculation.

---

## Country Escalation Matrices

View at **Admin → Escalation Matrices** (`/admin/escalation-matrices`).

| Country | Streams | Description |
|---------|:-------:|-------------|
| Kenya | 3 | Safaricom/Afyangu (citizens), Tiberbu (clinicians), SPICE/Medtronic LABS (HRIOs/CHWs) — all converge at Product Team |
| Bangladesh | 2 | SPICE field support (Shashtya Kormi/CHCP) + Internal Technical Escalation (L1–L4) |
| Sierra Leone | 1 | Cascading chiefdom → district → national → LABS Ops/MoH → Product Team |
| Other countries | — | Configurable via the admin UI |

---

## Channels & Integrations

### WhatsApp (Conversational Bot)

**Setup:**
1. Create a Meta Business account and a WhatsApp Business app at [developers.facebook.com](https://developers.facebook.com)
2. Add your phone number and get the Phone Number ID
3. Generate a system user token (permanent access token)
4. Set in `.env`:
   ```
   WHATSAPP_TOKEN=your_permanent_token
   WHATSAPP_PHONE_ID=your_phone_number_id
   WHATSAPP_VERIFY_TOKEN=medtronic_verify
   ```
5. Register the webhook URL on Meta: `https://your-domain.com/webhooks/whatsapp`
   - Verify token: the value of `WHATSAPP_VERIFY_TOKEN`
   - Subscribe to: `messages`

**User conversation flow:**

```
User: Hi
Bot:  Hello! Welcome to Medtronic LABS Support 🏥
      1️⃣ SPICE  2️⃣ Tiberbu  3️⃣ Afyangu  4️⃣ Other

User: 1
Bot:  Got it — SPICE. Describe your issue...

User: Cannot log in on the mobile app
Bot:  Summary: App=SPICE, Issue=Cannot log in...
      Reply YES to submit or NO to cancel.

User: YES
Bot:  ✅ Ticket TKT-20260609-0042 created. Reply STATUS to check.
```

Agents view all conversations at **Channels & Engagement → WhatsApp Inbox** and reply from the dashboard. When a ticket is resolved, a CSAT survey is automatically sent back to the user's WhatsApp.

### Embeddable In-App Widget

Drop one line into SPICE, Tiberbu, or any web app:

```html
<script src="https://your-support-domain.com/static/widget/support-widget.js"
        data-base-url="https://your-support-domain.com"
        data-app="SPICE"
        data-primary-color="#1d6fa4">
</script>
```

The widget:
1. Shows a floating **?** button (bottom-right)
2. On click, opens a panel with a KB article search
3. If no articles resolve the issue, presents a pre-filled ticket form (app name and current page URL captured automatically)
4. On ticket creation, switches to a status tracker with star rating

No dependencies. Uses Shadow DOM for full CSS isolation from the host app. Full-screen on mobile.

**Widget API endpoints** (CORS-enabled, no auth required):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/widget/config` | Branding, categories, countries |
| `GET` | `/widget/search?q=` | Knowledge base article search |
| `POST` | `/widget/ticket` | Create a ticket |
| `GET` | `/widget/ticket/<sl_no>` | Track ticket status |
| `POST` | `/widget/csat/<token>` | Submit a star rating |

### Email Inbound

| Mode | Endpoint |
|------|---------|
| Webhook | `POST /integrations/email/inbound` |
| IMAP polling | `GET /integrations/email/poll?key=<IMAP_POLL_KEY>` |

Duplicate emails are detected by `Message-ID` header.

### Telegram Bot

1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the token to `TELEGRAM_BOT_TOKEN`.
2. Register the webhook:
   ```
   POST https://api.telegram.org/bot<TOKEN>/setWebhook
        ?url=https://your-domain/integrations/telegram/webhook
   ```

### REST API

```bash
curl -X POST https://your-domain/tickets/api/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "issue_type": "Login / Access",
    "problem_details": "Cannot log into SPICE mobile app.",
    "priority": "High",
    "reporter_name": "Jane Doe",
    "email": "jane@example.com"
  }'
```

Response: `{"status": "success", "ticket_id": 42, "sl_no": "TKT-20260609-0042"}`

---

## Intelligent Support Features

### Proactive Nudges (Automatic)

Two background jobs run continuously without any configuration:

| Job | Frequency | What it does |
|-----|-----------|-------------|
| Aging Alert | Every 30 min | Sends an in-app notification to the assigned agent for any P1/P2/Urgent ticket with no first response after 2 hours |
| CSAT Dispatch | Every 60 min | Sends a WhatsApp CSAT survey to any user whose ticket was resolved via WhatsApp >1 hour ago and has not yet received a survey |

### Broadcasts

Admins can send proactive WhatsApp messages to field staff at **Channels & Engagement → Broadcasts**:
- Filter recipients by country (multi-select or all)
- Filter by role (DSO, Reporter, Admin, or all)
- Preview the formatted WhatsApp message before sending
- Full delivery history with recipient count and status

### CSAT Tracking

Ratings are collected through three channels:
- **WhatsApp** — bot sends "rate 1–5" message after resolution; reply captured in state machine
- **Widget** — inline star rating shown after ticket status = Resolved
- **Email** — link to rating page included in resolution email

View the full CSAT dashboard at **Channels & Engagement → CSAT Ratings**:
- Average score with colour indicator (green ≥4, yellow 3–4, red <3)
- Score distribution horizontal bar chart
- 30-day trend line chart
- Agent performance leaderboard
- Recent ratings with feedback text

### Nudge Log

Every nudge sent — CSAT surveys, aging alerts, and broadcasts — is recorded at `/admin/nudge-log` with delivery status and any response received.

---

## Feature Reference

### Automation Rules (`/admin/automation`)

**Trigger events:** `ticket_created`, `status_changed`, `priority_changed`, `reply_received`

**Condition fields:** `priority`, `current_status`, `channel`, `category_id`, `issue_type`, `problem_details`, `escalation_level`

**Action types:**

| Action | Params |
|--------|--------|
| `set_priority` | `{"priority": "Critical"}` |
| `set_status` | `{"status": "In Progress"}` |
| `assign_to` | `{"user_id": 5}` |
| `add_tag` | `{"tag_id": 3}` |
| `escalate` | `{"level": 2}` |
| `add_internal_note` | `{"body": "Auto-escalated by rule"}` |
| `notify_staff` | `{"message": "Urgent ticket needs attention"}` |
| `send_email_reporter` | `{"subject": "Update on {sl_no}", "body": "We are investigating."}` |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `N` | New Ticket |
| `I` | Inbox |
| `D` | Dashboard |
| `R` | Reports |
| `/` | Focus search |
| `Alt+T` | Toggle dark/light mode |
| `?` | Show shortcuts help |

### Dark Mode

Click the moon icon in the top navbar or press `Alt+T`. Saved in `localStorage`, applied on page load with no flash.

### Excel Export

Download a formatted `.xlsx` file from the sidebar or `/tickets/export-excel`. Applies the same filters as the current view. Column headers are colour-coded by status.

### GDPR Compliance

- **Export your data** — `/account/preferences` → "Export My Data (JSON)"
- **Right to be forgotten** — Super Admins anonymize any account from `/admin/users`

---

## License

Internal use — Medtronic Labs.
