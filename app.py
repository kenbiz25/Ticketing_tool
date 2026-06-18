import os
import secrets
from flask import Flask
from flask_login import LoginManager, current_user
from werkzeug.security import generate_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from config import Config
from extensions import limiter
from models import (
    db, User, Role, SLAPolicy, Country, AdminLevel1, IssueCategory, IssueSubcategory,
    TicketLink, SavedView, CustomField, TicketFieldValue, TimeEntry,
    TelegramSession, CallLog,
    AutomationRule, KBCategory, KBArticle, KBArticleFeedback,
    BrandingSettings, LoginAuditLog, UserRegionRole, CountryEscalationMatrix,
    NudgeLog, BroadcastMessage,
)
from routes.auth import auth
from routes.tickets import tickets
from routes.dashboard import dashboard
from routes.notifications import notifs
from routes.admin_tools import admin_tools
from routes.integrations import integrations
from routes.automation import automation
from routes.kb import kb
from routes.webhooks import webhooks
from routes.widget_api import widget_api
from routes.nudges import nudges


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    limiter.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        unread = 0
        if current_user.is_authenticated:
            from models import Notification
            unread = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
        branding = None
        try:
            branding = BrandingSettings.get()
        except Exception:
            pass
        return {"unread_notifications": unread, "branding": branding}

    app.register_blueprint(auth)
    app.register_blueprint(tickets)
    app.register_blueprint(dashboard)
    app.register_blueprint(notifs)
    app.register_blueprint(admin_tools)
    app.register_blueprint(integrations)

    app.register_blueprint(automation)
    app.register_blueprint(kb)
    app.register_blueprint(webhooks)
    app.register_blueprint(widget_api)
    app.register_blueprint(nudges)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        db.create_all()
        if db.engine.dialect.name == "sqlite":
         _migrate_db()
        _seed_superadmin()
        _seed_sla_policies()
        _seed_countries()
        _seed_issue_taxonomy()
        _seed_escalation_matrices()

    scheduler = BackgroundScheduler(daemon=True)

    def _job_aging_alert():
        with app.app_context():
            _check_aging_tickets(app)

    def _job_csat_dispatch():
        with app.app_context():
            _dispatch_wa_csat(app)

    scheduler.add_job(_job_aging_alert, 'interval', minutes=30, id='aging_alert', replace_existing=True)
    scheduler.add_job(_job_csat_dispatch, 'interval', minutes=60, id='csat_dispatch', replace_existing=True)
    if not scheduler.running:
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown(wait=False))

    return app


def _migrate_db():
    """Add columns introduced after the initial schema without requiring a full DB reset."""
    engine = db.engine
    with engine.connect() as conn:
        def _cols(table):
            rows = conn.execute(db.text(f"PRAGMA table_info({table})")).fetchall()
            return {r[1] for r in rows}

        def _add(table, col, typedef):
            if col not in _cols(table):
                conn.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}"))

        # ── tickets: columns added across phases ───────────────────────────
        _add("tickets", "channel",             "VARCHAR(20) DEFAULT 'web'")
        _add("tickets", "external_id",         "VARCHAR(200)")
        _add("tickets", "country_id",          "INTEGER")
        _add("tickets", "admin1_id",           "INTEGER")
        _add("tickets", "admin2_id",           "INTEGER")
        _add("tickets", "admin3_id",           "INTEGER")
        _add("tickets", "category_id",         "INTEGER")
        _add("tickets", "subcategory_id",      "INTEGER")
        _add("tickets", "task_initial_status", "VARCHAR(50) DEFAULT 'New'")
        _add("tickets", "escalation_level",    "INTEGER DEFAULT 0")
        _add("tickets", "notification_sent",   "BOOLEAN DEFAULT 0")
        _add("tickets", "last_notification_at","DATETIME")
        _add("tickets", "due_date",            "DATETIME")
        _add("tickets", "first_response_at",   "DATETIME")
        _add("tickets", "sla_breached",        "BOOLEAN DEFAULT 0")
        _add("tickets", "locked_by_id",        "INTEGER")
        _add("tickets", "locked_at",           "DATETIME")
        _add("tickets", "parent_id",           "INTEGER")

        # ── users: columns added in later phases ───────────────────────────
        _add("users", "timezone", "VARCHAR(50) DEFAULT 'UTC'")
        _add("users", "language", "VARCHAR(10) DEFAULT 'en'")

        # ── countries: business hours per country ──────────────────────────
        _add("countries", "timezone",        "VARCHAR(50) DEFAULT 'Africa/Nairobi'")
        _add("countries", "work_start_hour", "INTEGER DEFAULT 8")
        _add("countries", "work_end_hour",   "INTEGER DEFAULT 17")
        _add("countries", "working_days",    "VARCHAR(20) DEFAULT 'Mon-Fri'")

        # ── sla_policies: escalation matrix columns ──────────────────────────
        _add("sla_policies", "code",                  "VARCHAR(10)")
        _add("sla_policies", "severity",              "VARCHAR(30)")
        _add("sla_policies", "definition",            "TEXT")
        _add("sla_policies", "l1_owner",              "VARCHAR(100)")
        _add("sla_policies", "l2_resolution_hours",   "REAL")
        _add("sla_policies", "l3_resolution_hours",   "REAL")
        _add("sla_policies", "l4_resolution_hours",   "REAL")
        _add("sla_policies", "auto_escalate",         "BOOLEAN DEFAULT 0")
        _add("sla_policies", "auto_escalate_note",    "VARCHAR(100)")
        _add("sla_policies", "notification_rule",     "TEXT")
        _add("sla_policies", "is_24_7",               "BOOLEAN DEFAULT 0")
        _add("sla_policies", "display_order",         "INTEGER DEFAULT 0")

        # ── country_escalation_matrices table ────────────────────────────────────
        # Created by db.create_all() — no ALTER needed, it's a new table

        # ── tickets: WhatsApp and widget columns ────────────────────────────────
        _add("tickets", "whatsapp_phone",  "VARCHAR(30)")
        _add("tickets", "widget_app",      "VARCHAR(50)")
        _add("tickets", "widget_page",     "VARCHAR(500)")
        _add("tickets", "csat_sent_via",   "VARCHAR(20)")

        conn.commit()


def _seed_sla_policies():
    # Business day = 8 working hours (08:00–17:00 EAT Mon–Fri, excl. P1/P2 which run 24/7)
    MATRIX = [
        dict(
            priority="Critical", code="P1", severity="CRITICAL", display_order=1,
            definition="System inaccessible for 10+ users. Data loss risk. Production outage.",
            l1_owner="County ICT / HRIO",
            first_response_hours=0.25,   # 15 min
            resolution_hours=1.0,         # L1: 1 hour
            l2_resolution_hours=2.0,      # L2: 2 hours
            l3_resolution_hours=4.0,      # L3: 4 hours
            l4_resolution_hours=8.0,      # L4: 8 hours
            auto_escalate=True, auto_escalate_note="YES → L3 immediately",
            notification_rule="DHA PM + L4 alerted instantly",
            is_24_7=True,
        ),
        dict(
            priority="High", code="P2", severity="HIGH", display_order=2,
            definition="Core module unavailable for county/facility. No workaround exists.",
            l1_owner="County ICT",
            first_response_hours=1.0,
            resolution_hours=4.0,         # L1: 4 hours
            l2_resolution_hours=8.0,      # L2: 8 hours
            l3_resolution_hours=24.0,     # L3: 1 business day
            l4_resolution_hours=48.0,     # L4: 2 business days
            auto_escalate=True, auto_escalate_note="If L1 breaches SLA",
            notification_rule="L2 + DHA PM notified",
            is_24_7=True,
        ),
        dict(
            priority="Medium", code="P3", severity="MEDIUM", display_order=3,
            definition="Degraded functionality. Workaround available. Affects subset of users.",
            l1_owner="TOT / County ICT",
            first_response_hours=4.0,
            resolution_hours=8.0,         # L1: 1 business day
            l2_resolution_hours=16.0,     # L2: 2 business days
            l3_resolution_hours=32.0,     # L3: 4 business days
            l4_resolution_hours=56.0,     # L4: 7 business days
            auto_escalate=True, auto_escalate_note="If L2 breaches SLA",
            notification_rule="L2 notified on breach",
            is_24_7=False,
        ),
        dict(
            priority="Low", code="P4", severity="LOW", display_order=4,
            definition="Cosmetic issue. No operational impact. Single user affected.",
            l1_owner="TOT / Facility",
            first_response_hours=8.0,     # 1 business day
            resolution_hours=24.0,        # L1: 3 business days
            l2_resolution_hours=40.0,     # L2: 5 business days
            l3_resolution_hours=80.0,     # L3: 10 business days
            l4_resolution_hours=None,     # L4: Scheduled
            auto_escalate=False, auto_escalate_note="No auto-escalation",
            notification_rule="Weekly digest",
            is_24_7=False,
        ),
        dict(
            priority="Enhancement", code="P5", severity="ENHANCEMENT", display_order=5,
            definition="Feature request or improvement suggestion. No current impact.",
            l1_owner="Any user",
            first_response_hours=16.0,    # 2 business days
            resolution_hours=None,        # Triage & route
            l2_resolution_hours=None,     # Sprint planning
            l3_resolution_hours=None,     # Scheduled
            l4_resolution_hours=None,     # Roadmap
            auto_escalate=False, auto_escalate_note="No auto-escalation",
            notification_rule="Quarterly roadmap review",
            is_24_7=False,
        ),
        dict(
            priority="OTP", code="OTP", severity="AUTO → L3", display_order=6,
            definition="One-Time Password failure. Authentication system error.",
            l1_owner="L1 logs, L3 assigned",
            first_response_hours=0.25,    # 15 min
            resolution_hours=None,        # Bypasses L2
            l2_resolution_hours=None,     # N/A
            l3_resolution_hours=2.0,      # L3: 2 hours
            l4_resolution_hours=4.0,      # L4: 4 hours
            auto_escalate=True, auto_escalate_note="YES → L3 immediately",
            notification_rule="L3 + L4 paged",
            is_24_7=True,
        ),
        dict(
            priority="Outage", code="OUTAGE", severity="AUTO → L4", display_order=7,
            definition="Full system down. Multi-county impact.",
            l1_owner="Any reporter",
            first_response_hours=0.083,   # Immediate (~5 min)
            resolution_hours=None,        # Bypasses L1/L2/L3
            l2_resolution_hours=None,     # N/A
            l3_resolution_hours=None,     # N/A
            l4_resolution_hours=2.0,      # L4: 2 hours
            auto_escalate=True, auto_escalate_note="YES → L4 immediately",
            notification_rule="All stakeholders + DHA emergency",
            is_24_7=True,
        ),
        # Keep Urgent mapped to same as P1 for backward compat with existing tickets
        dict(
            priority="Urgent", code="P1", severity="CRITICAL", display_order=0,
            definition="Same as P1 Critical — system inaccessible, data loss risk.",
            l1_owner="County ICT / HRIO",
            first_response_hours=0.25,
            resolution_hours=1.0,
            l2_resolution_hours=2.0,
            l3_resolution_hours=4.0,
            l4_resolution_hours=8.0,
            auto_escalate=True, auto_escalate_note="YES → L3 immediately",
            notification_rule="DHA PM + L4 alerted instantly",
            is_24_7=True,
        ),
    ]
    for entry in MATRIX:
        policy = SLAPolicy.query.filter_by(priority=entry["priority"]).first()
        if not policy:
            policy = SLAPolicy(priority=entry["priority"])
            db.session.add(policy)
        for k, v in entry.items():
            if k != "priority":
                setattr(policy, k, v)
    db.session.commit()


def _seed_countries():
    COUNTRIES = [
        {
            "name": "Bangladesh", "code": "BD",
            "admin1_label": "Division", "admin2_label": "District", "admin3_label": "Upazila",
            "level1": ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"],
        },
        {
            "name": "Kenya", "code": "KE",
            "admin1_label": "County", "admin2_label": "Sub-county", "admin3_label": "Ward",
            "level1": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Uasin Gishu", "Machakos",
                       "Nyeri", "Meru", "Kilifi", "Kakamega", "Bungoma", "Kisii"],
        },
        {
            "name": "India", "code": "IN",
            "admin1_label": "State", "admin2_label": "District", "admin3_label": "Block",
            "level1": ["Andhra Pradesh", "Bihar", "Delhi", "Gujarat", "Karnataka",
                       "Kerala", "Madhya Pradesh", "Maharashtra", "Odisha",
                       "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
                       "Uttar Pradesh", "West Bengal"],
        },
        {
            "name": "Bhutan", "code": "BT",
            "admin1_label": "Dzongkhag", "admin2_label": "Dungkhag", "admin3_label": "Gewog",
            "level1": ["Bumthang", "Chhukha", "Dagana", "Gasa", "Haa", "Lhuntse",
                       "Mongar", "Paro", "Pemagatshel", "Punakha", "Samdrup Jongkhar",
                       "Samtse", "Sarpang", "Thimphu", "Trashigang", "Trashiyangtse",
                       "Trongsa", "Tsirang", "Wangdue Phodrang", "Zhemgang"],
        },
        {
            "name": "Sierra Leone", "code": "SL",
            "admin1_label": "Province", "admin2_label": "District", "admin3_label": "Chiefdom",
            "level1": ["Eastern Province", "Northern Province", "North West Province",
                       "Southern Province", "Western Area"],
        },
        {
            "name": "Tanzania", "code": "TZ",
            "admin1_label": "Region", "admin2_label": "District", "admin3_label": "Ward",
            "level1": ["Arusha", "Dar es Salaam", "Dodoma", "Geita", "Iringa",
                       "Kagera", "Katavi", "Kigoma", "Kilimanjaro", "Lindi",
                       "Manyara", "Mara", "Mbeya", "Morogoro", "Mtwara",
                       "Mwanza", "Njombe", "Pwani", "Rukwa", "Ruvuma",
                       "Shinyanga", "Simiyu", "Singida", "Songwe", "Tabora",
                       "Tanga", "Zanzibar North", "Zanzibar South", "Zanzibar West"],
        },
        {
            "name": "Rwanda", "code": "RW",
            "admin1_label": "Province", "admin2_label": "District", "admin3_label": "Sector",
            "level1": ["Kigali City", "Northern Province", "Southern Province",
                       "Eastern Province", "Western Province"],
        },
        {
            "name": "Saudi Arabia", "code": "SA",
            "admin1_label": "Region", "admin2_label": "Governorate", "admin3_label": "District",
            "level1": ["Riyadh", "Makkah", "Madinah", "Eastern Province", "Asir",
                       "Tabuk", "Hail", "Northern Borders", "Jazan", "Najran",
                       "Al Bahah", "Al Jawf", "Qassim"],
        },
    ]

    for cd in COUNTRIES:
        c = Country.query.filter_by(code=cd["code"]).first()
        if not c:
            c = Country(
                name=cd["name"], code=cd["code"],
                admin1_label=cd["admin1_label"],
                admin2_label=cd["admin2_label"],
                admin3_label=cd["admin3_label"],
            )
            db.session.add(c)
            db.session.flush()
        for l1_name in cd.get("level1", []):
            if not AdminLevel1.query.filter_by(name=l1_name, country_id=c.id).first():
                db.session.add(AdminLevel1(name=l1_name, country_id=c.id))
    db.session.commit()


def _seed_issue_taxonomy():
    TAXONOMY = [
        ("Application Issues", "laptop-code", "danger", [
            "Login / Access", "Performance / Slowness", "Crash / App Error",
            "Data Sync Issue", "UI / Display Problem", "Offline Mode Issue",
        ]),
        ("Data Issues", "database", "warning", [
            "Missing Records", "Incorrect / Corrupted Data",
            "Data Import / Export", "Duplicate Records",
        ]),
        ("Infrastructure", "server", "secondary", [
            "Network / Connectivity", "Server / Backend Down",
            "Hardware Problem", "SMS / Notification Delivery",
        ]),
        ("Feature Request", "lightbulb", "info", [
            "New Feature", "Enhancement to Existing Feature",
            "Workflow / Process Change",
        ]),
        ("Training / Process", "chalkboard-teacher", "success", [
            "User Training Query", "Process / Policy Question",
            "Documentation Request",
        ]),
        ("Other", "question-circle", "primary", [
            "General Inquiry", "Unclassified",
        ]),
    ]
    for order, (cat_name, icon, color, subs) in enumerate(TAXONOMY):
        cat = IssueCategory.query.filter_by(name=cat_name).first()
        if not cat:
            cat = IssueCategory(name=cat_name, icon=icon, color=color, display_order=order)
            db.session.add(cat)
            db.session.flush()
        for sub_order, sub_name in enumerate(subs):
            from models import IssueSubcategory
            if not IssueSubcategory.query.filter_by(name=sub_name, category_id=cat.id).first():
                db.session.add(IssueSubcategory(
                    name=sub_name, category_id=cat.id, display_order=sub_order
                ))
    db.session.commit()


def _seed_escalation_matrices():
    from models import CountryEscalationMatrix, Country

    SL_MATRIX = {
        "levels": [
            {
                "name": "Medtronic Labs — Product",
                "owner": "Product Engineering Team",
                "tool": "Jira", "tool_color": "#dcfce7", "tool_text": "#166534",
                "color": "#f9fafb", "border": "#d1d5db", "actions": []
            },
            {
                "name": "Medtronic LABS Support",
                "owner": "LABS Central Support",
                "tool": "UV Desk / ITSM", "tool_color": "#dbeafe", "tool_text": "#1e40af",
                "color": "#f9fafb", "border": "#d1d5db", "actions": []
            },
            {
                "name": "LABS Ops Associates · Ministry of Health SL",
                "owner": "LABS Ops Leads, MoH SL",
                "tool": "UV Desk", "tool_color": "#dbeafe", "tool_text": "#1e40af",
                "color": "#eff6ff", "border": "#3b82f6",
                "actions": ["Access to tools and data", "Policy oversight"]
            },
            {
                "name": "L2 — District Level Support / CHW Focal",
                "owner": "District Health Information Officer",
                "tool": "UV Desk", "tool_color": "#dbeafe", "tool_text": "#1e40af",
                "color": "#dcfce7", "border": "#16a34a",
                "actions": [
                    "Use data for decision making",
                    "Empower on decision making",
                    "Train on tools and materials for better ownership",
                    "Enable visibility and continuous collaboration"
                ]
            },
            {
                "name": "L1 — Chiefdom Level Support",
                "owner": "Peer Supervisor / PHU Level Staff",
                "tool": "WhatsApp / Forms", "tool_color": "#dcfce7", "tool_text": "#166534",
                "color": "#fef3c7", "border": "#d97706",
                "actions": [
                    "Facilitating WhatsApp group creation",
                    "Empower on resolving escalations",
                    "Improve district visibility",
                    "Use forms to complement issues escalated",
                    "Monthly District CHW meetings for continuous support"
                ]
            },
            {
                "name": "Users — CHW · PHU Level Staff",
                "owner": "Community Health Workers",
                "tool": None,
                "color": "#eff6ff", "border": "#3b82f6",
                "actions": ["Continuous sharing of material based on arising issues"]
            },
        ],
        "notes": "Sierra Leone uses a cascading district-to-national escalation. L1 is resolved at chiefdom level by peer supervisors. Issues unresolved within SLA escalate via UV Desk to district (L2), then to national LABS Ops and Ministry of Health SL."
    }

    KE_MATRIX = {
        "streams": [
            {
                "name": "Ministry of Health — Afyangu (Safaricom)",
                "header_color": "#166534",
                "header_text": "#ffffff",
                "logo_icon": "landmark",
                "users": ["Kenyan Citizens"],
                "levels": [
                    {
                        "name": "L3 — Engineers",
                        "owner": "Senior Technical Engineers",
                        "tool": None,
                        "color": "#dcfce7", "border": "#16a34a",
                        "actions": ["System-level fixes", "Architecture decisions"]
                    },
                    {
                        "name": "L2 — Technical Desk",
                        "owner": "Technical Support Team",
                        "tool": None,
                        "color": "#dcfce7", "border": "#16a34a",
                        "actions": ["Technical troubleshooting", "Configuration issues"]
                    },
                    {
                        "name": "L1 — Phone Support",
                        "owner": "Phone Support Agents",
                        "tool": "Calls", "tool_color": "#dcfce7", "tool_text": "#166534",
                        "color": "#dcfce7", "border": "#16a34a",
                        "actions": ["First contact resolution", "Basic troubleshooting", "Ticket logging"]
                    }
                ]
            },
            {
                "name": "tiberbu — Facility Staff",
                "header_color": "#7c3aed",
                "header_text": "#ffffff",
                "logo_icon": "hospital",
                "users": ["Clinicians", "Nurses"],
                "levels": [
                    {
                        "name": "Engineers L1",
                        "owner": "Technical Engineering Level 1",
                        "tool": None,
                        "color": "#f3e8ff", "border": "#7c3aed",
                        "actions": ["Advanced technical resolution", "Escalation to Product Team"]
                    },
                    {
                        "name": "Junior Dev / ITOps — Implementation Team",
                        "owner": "Implementation & DevOps Team",
                        "tool": "Calls / WhatsApp", "tool_color": "#fef3c7", "tool_text": "#92400e",
                        "color": "#f3e8ff", "border": "#7c3aed",
                        "actions": ["Implementation support", "Configuration", "On-site escalation handling"]
                    },
                    {
                        "name": "Sub-county ICT / HRIOs / ToTs",
                        "owner": "Sub-county Health Records Officers, Trainers",
                        "tool": "WhatsApp", "tool_color": "#dcfce7", "tool_text": "#166534",
                        "color": "#f3e8ff", "border": "#7c3aed",
                        "actions": ["First facility-level support", "Trainer assistance", "HRIO coordination"]
                    },
                    {
                        "name": "Facility tiberbu Admins",
                        "owner": "Facility-level tiberbu Administrators",
                        "tool": None,
                        "color": "#f3e8ff", "border": "#7c3aed",
                        "actions": ["User account management", "Basic troubleshooting", "Issue documentation"]
                    }
                ]
            }
        ],
        "shared_levels": [
            {
                "name": "Product Team — Medtronic Labs",
                "owner": "Product Engineering, Mobile / Web Platform",
                "tool": "Jira + ITSM", "tool_color": "#dbeafe", "tool_text": "#1e40af",
                "color": "#f9fafb", "border": "#d1d5db",
                "actions": ["Platform updates", "Bug fixes", "Feature delivery", "Both streams feed here"]
            }
        ],
        "notes": "Kenya has two parallel support streams: Ministry of Health (Afyangu/Safaricom) serving Kenyan Citizens via phone support, and tiberbu serving clinical staff through facility admins and HRIOs. Both streams escalate to the shared Medtronic Labs Product Team via Jira."
    }

    sl = Country.query.filter_by(code="SL").first()
    if sl:
        existing = CountryEscalationMatrix.query.filter_by(country_id=sl.id).first()
        if not existing:
            db.session.add(CountryEscalationMatrix(
                country_id=sl.id,
                levels_json=SL_MATRIX["levels"],
                notes=SL_MATRIX["notes"],
            ))

    ke = Country.query.filter_by(code="KE").first()
    if ke:
        existing = CountryEscalationMatrix.query.filter_by(country_id=ke.id).first()
        if not existing:
            db.session.add(CountryEscalationMatrix(
                country_id=ke.id,
                levels_json=KE_MATRIX.get("shared_levels", []),
                streams_json=KE_MATRIX.get("streams", []),
                notes=KE_MATRIX["notes"],
            ))

    db.session.commit()


def _check_aging_tickets(app):
    """Alert agents about P1/P2 tickets with no first response after 2h."""
    try:
        from models import Ticket, Notification, SLAPolicy
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=2)
        aging = Ticket.query.filter(
            Ticket.current_status.notin_(["Resolved", "Closed"]),
            Ticket.priority.in_(["Critical", "High", "Urgent"]),
            Ticket.first_response_at.is_(None),
            Ticket.created_at < cutoff,
            Ticket.assigned_to_id.isnot(None)
        ).all()
        for t in aging:
            existing = Notification.query.filter_by(
                ticket_id=t.id, notif_type="aging_alert"
            ).first()
            if not existing:
                db.session.add(Notification(
                    user_id=t.assigned_to_id,
                    ticket_id=t.id,
                    message=f"SLA Alert: {t.sl_no} ({t.priority}) has had no response for >2h",
                    notif_type="aging_alert"
                ))
        db.session.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Aging check failed: {e}")


def _dispatch_wa_csat(app):
    """Send WhatsApp CSAT surveys for tickets resolved >1h ago without a rating."""
    try:
        from models import Ticket, CSATRating, WhatsAppSession, NudgeLog
        from routes.webhooks import _wa_send
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=1)
        resolved = Ticket.query.filter(
            Ticket.current_status.in_(["Resolved", "Closed"]),
            Ticket.solved_date < cutoff,
            Ticket.issue_reporter_contact.isnot(None),
            Ticket.channel == "whatsapp"
        ).all()
        for t in resolved:
            csat = CSATRating.query.filter_by(ticket_id=t.id).first()
            if csat and csat.submitted_at:
                continue
            already_sent = NudgeLog.query.filter_by(
                ticket_id=t.id, nudge_type="csat_whatsapp"
            ).first()
            if already_sent:
                continue
            phone = t.issue_reporter_contact
            if not phone or "@" in phone:
                continue
            if not csat:
                import secrets
                csat = CSATRating(ticket_id=t.id)
                db.session.add(csat)
                db.session.flush()
            session = WhatsAppSession.query.filter_by(phone=phone).first()
            if session:
                session.state = "CSAT_PENDING"
                session.data = {**(session.data or {}), "ticket_id": t.id}
            msg = (
                f"Hi! Your ticket *{t.sl_no}* has been resolved.\n\n"
                f"How satisfied are you with the support?\n"
                f"Reply: 5=Excellent 4=Good 3=Average 2=Poor 1=Very Poor"
            )
            _wa_send(phone, msg)
            db.session.add(NudgeLog(
                ticket_id=t.id, nudge_type="csat_whatsapp",
                recipient=phone, channel="whatsapp",
                message_preview=f"CSAT for {t.sl_no}", status="sent"
            ))
        db.session.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"CSAT dispatch failed: {e}")


def _seed_superadmin():
    if not User.query.filter_by(username="superadmin").first():
        password = os.getenv("SUPERADMIN_PASSWORD") or secrets.token_urlsafe(14)
        admin = User(
            username="superadmin",
            password_hash=generate_password_hash(password),
            full_name="Super Administrator",
            role=Role.SUPER_ADMIN,
            email=os.getenv("ADMIN_EMAIL", "admin@example.com"),
        )
        db.session.add(admin)
        db.session.commit()
        if not os.getenv("SUPERADMIN_PASSWORD"):
            print(f"[SECURITY] Default super admin created — username: superadmin / password: {password}")
            print("[SECURITY] Set SUPERADMIN_PASSWORD in .env to control this. Change the password after first login.")


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
