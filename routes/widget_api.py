from flask import Blueprint, request, jsonify, current_app, make_response
from models import (
    db, Ticket, KBArticle, KBCategory, CSATRating,
    BrandingSettings, IssueCategory, Country, TicketComment,
)
from datetime import datetime

widget_api = Blueprint("widget_api", __name__, url_prefix="/widget")


# ── CORS ────────────────────────────────────────────────────────────────────────

def _cors_origin():
    """Return the Access-Control-Allow-Origin value for the current request.

    When WIDGET_ALLOWED_ORIGINS is '*' (default) every origin is allowed.
    Otherwise only origins in the comma-separated allowlist are reflected;
    unrecognised origins get no CORS header and the browser will block them.
    """
    allowed = current_app.config.get("WIDGET_ALLOWED_ORIGINS", "*").strip()
    if allowed == "*":
        return "*"
    origin = request.headers.get("Origin", "")
    allowed_set = {o.strip() for o in allowed.split(",") if o.strip()}
    return origin if origin in allowed_set else None


@widget_api.after_request
def add_cors_headers(response):
    origin = _cors_origin()
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        if origin != "*":
            response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Widget-Token"
    return response


@widget_api.route("/<path:subpath>", methods=["OPTIONS"])
@widget_api.route("/", methods=["OPTIONS"])
def handle_options(subpath=None):
    return jsonify({}), 200


# ── GET /widget/config ──────────────────────────────────────────────────────────

@widget_api.route("/config", methods=["GET"])
def widget_config():
    branding = BrandingSettings.get()
    categories = KBCategory.query.filter_by(is_active=True).order_by(KBCategory.display_order).all()
    countries = Country.query.filter_by(is_active=True).order_by(Country.name).all()

    return jsonify({
        "app_name": branding.app_name,
        "primary_color": branding.primary_color,
        "categories": [
            {"id": c.id, "name": c.name, "icon": c.icon}
            for c in categories
        ],
        "countries": [
            {"id": co.id, "name": co.name, "code": co.code}
            for co in countries
        ],
    })


# ── GET /widget/search ──────────────────────────────────────────────────────────

@widget_api.route("/search", methods=["GET"])
def widget_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})

    pattern = f"%{q}%"
    articles = (
        KBArticle.query
        .filter(
            KBArticle.is_published == True,
            db.or_(
                KBArticle.title.ilike(pattern),
                KBArticle.body_html.ilike(pattern),
            ),
        )
        .limit(5)
        .all()
    )

    results = []
    for a in articles:
        results.append({
            "id": a.id,
            "title": a.title,
            "slug": a.slug,
            "meta_description": a.meta_description,
            "category_name": a.category.name if a.category else None,
        })

    return jsonify({"results": results})


# ── POST /widget/ticket ─────────────────────────────────────────────────────────

@widget_api.route("/ticket", methods=["POST"])
def create_ticket():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()

    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 422
    if not description:
        return jsonify({"ok": False, "error": "description is required"}), 422

    contact = (data.get("contact") or "").strip()
    email = (data.get("email") or "").strip() or None
    app_name = (data.get("app") or "").strip() or None
    page = (data.get("page") or "").strip() or None
    priority = (data.get("priority") or "Medium").strip()
    category_id = data.get("category_id") or None
    country_id = data.get("country_id") or None

    now = datetime.utcnow()
    sl_no = Ticket.generate_sl_no()

    ticket = Ticket(
        sl_no=sl_no,
        channel="widget",
        widget_app=app_name,
        widget_page=page,
        issue_reporter_name=name,
        issue_reporter_contact=contact,
        form_submit_email=email,
        problem_details=description,
        priority=priority,
        category_id=category_id,
        country_id=country_id,
        current_status="Open",
        reporting_date=now,
        issue_start_date=now,
        created_at=now,
        updated_at=now,
    )

    db.session.add(ticket)
    db.session.commit()

    return jsonify({"ok": True, "ticket_id": ticket.id, "sl_no": ticket.sl_no}), 201


# ── GET /widget/ticket/<sl_no> ──────────────────────────────────────────────────

@widget_api.route("/ticket/<sl_no>", methods=["GET"])
def get_ticket(sl_no):
    ticket = Ticket.query.filter_by(sl_no=sl_no).first()
    if not ticket:
        return jsonify({"ok": False, "error": "Ticket not found"}), 404

    # Determine last update: latest public comment or ticket updated_at
    last_comment = (
        TicketComment.query
        .filter_by(ticket_id=ticket.id, is_internal=False)
        .order_by(TicketComment.created_at.desc())
        .first()
    )
    if last_comment:
        last_update = last_comment.created_at.isoformat()
    else:
        last_update = ticket.updated_at.isoformat() if ticket.updated_at else None

    return jsonify({
        "sl_no": ticket.sl_no,
        "status": ticket.current_status,
        "priority": ticket.priority,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "solved_date": ticket.solved_date.isoformat() if ticket.solved_date else None,
        "sla_status": ticket.sla_status(),
        "last_update": last_update,
    })


# ── POST /widget/csat/<token> ───────────────────────────────────────────────────

@widget_api.route("/csat/<token>", methods=["POST"])
def submit_csat(token):
    csat = CSATRating.query.filter_by(token=token).first()
    if not csat:
        return jsonify({"ok": False, "error": "Invalid token"}), 404

    if csat.submitted_at is not None:
        return jsonify({"ok": False, "error": "Already rated"}), 409

    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    feedback = data.get("feedback") or None

    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"ok": False, "error": "rating must be an integer between 1 and 5"}), 422

    csat.rating = rating
    csat.feedback = feedback
    csat.submitted_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"ok": True})
