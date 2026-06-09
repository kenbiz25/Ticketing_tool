import re
from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, abort,
)
from flask_login import login_required, current_user

from models import db, KBCategory, KBArticle, KBArticleFeedback, User

kb = Blueprint("kb", __name__)


def _slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return re.sub(r"^-+|-+$", "", text)


def _unique_slug(base, model, exclude_id=None):
    slug = base
    i = 1
    while True:
        q = model.query.filter_by(slug=slug)
        if exclude_id:
            q = q.filter(model.id != exclude_id)
        if not q.first():
            return slug
        slug = f"{base}-{i}"
        i += 1


# ─── Public KB Routes ─────────────────────────────────────────────────────────

@kb.route("/kb/")
def kb_index():
    categories = (
        KBCategory.query
        .filter_by(is_active=True)
        .order_by(KBCategory.display_order, KBCategory.name)
        .all()
    )
    q = request.args.get("q", "").strip()
    results = []
    if q:
        term = f"%{q}%"
        results = (
            KBArticle.query
            .filter_by(is_published=True)
            .filter(db.or_(
                KBArticle.title.ilike(term),
                KBArticle.body_html.ilike(term),
                KBArticle.meta_description.ilike(term),
            ))
            .order_by(KBArticle.view_count.desc())
            .limit(20)
            .all()
        )
    return render_template("kb/index.html", categories=categories, results=results, q=q)


@kb.route("/kb/category/<slug>")
def kb_category(slug):
    cat = KBCategory.query.filter_by(slug=slug, is_active=True).first_or_404()
    articles = (
        cat.articles
        .filter_by(is_published=True)
        .order_by(KBArticle.title)
        .all()
    )
    return render_template("kb/category.html", category=cat, articles=articles)


@kb.route("/kb/article/<slug>")
def kb_article(slug):
    article = KBArticle.query.filter_by(slug=slug, is_published=True).first_or_404()
    article.view_count = (article.view_count or 0) + 1
    db.session.commit()
    related = (
        KBArticle.query
        .filter_by(category_id=article.category_id, is_published=True)
        .filter(KBArticle.id != article.id)
        .order_by(KBArticle.view_count.desc())
        .limit(5)
        .all()
    )
    user_voted = False
    ip = request.remote_addr
    if ip:
        user_voted = KBArticleFeedback.query.filter_by(
            article_id=article.id, ip_address=ip
        ).first() is not None
    return render_template("kb/article.html", article=article, related=related, user_voted=user_voted)


@kb.route("/kb/article/<int:article_id>/feedback", methods=["POST"])
def kb_feedback(article_id):
    article = KBArticle.query.get_or_404(article_id)
    ip = request.remote_addr or "unknown"
    already = KBArticleFeedback.query.filter_by(article_id=article_id, ip_address=ip).first()
    if already:
        return jsonify({"ok": False, "msg": "Already voted"})
    helpful = request.json.get("helpful", True)
    db.session.add(KBArticleFeedback(
        article_id=article_id, ip_address=ip, is_helpful=bool(helpful)
    ))
    if helpful:
        article.helpful_yes = (article.helpful_yes or 0) + 1
    else:
        article.helpful_no = (article.helpful_no or 0) + 1
    db.session.commit()
    return jsonify({"ok": True, "yes": article.helpful_yes, "no": article.helpful_no})


# ─── Admin KB Routes ──────────────────────────────────────────────────────────

@kb.route("/admin/kb")
@login_required
def kb_admin_articles():
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.main"))
    articles = (
        KBArticle.query
        .join(KBCategory)
        .order_by(KBCategory.name, KBArticle.title)
        .all()
    )
    return render_template("admin/kb_articles.html", articles=articles)


@kb.route("/admin/kb/article/create", methods=["GET", "POST"])
@login_required
def kb_create_article():
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.main"))
    categories = KBCategory.query.filter_by(is_active=True).order_by(KBCategory.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "warning")
            return render_template("admin/kb_article_edit.html", article=None, categories=categories)
        slug = _unique_slug(_slugify(title), KBArticle)
        article = KBArticle(
            title=title,
            slug=slug,
            body_html=request.form.get("body_html", ""),
            meta_description=request.form.get("meta_description", "").strip(),
            category_id=int(request.form["category_id"]),
            is_published=request.form.get("is_published") == "on",
            created_by_id=current_user.id,
        )
        db.session.add(article)
        db.session.commit()
        flash(f"Article '{title}' created.", "success")
        return redirect(url_for("kb.kb_admin_articles"))
    return render_template("admin/kb_article_edit.html", article=None, categories=categories)


@kb.route("/admin/kb/article/<int:article_id>/edit", methods=["GET", "POST"])
@login_required
def kb_edit_article(article_id):
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.main"))
    article = KBArticle.query.get_or_404(article_id)
    categories = KBCategory.query.filter_by(is_active=True).order_by(KBCategory.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "warning")
            return render_template("admin/kb_article_edit.html", article=article, categories=categories)
        if title != article.title:
            article.slug = _unique_slug(_slugify(title), KBArticle, exclude_id=article.id)
        article.title = title
        article.body_html = request.form.get("body_html", "")
        article.meta_description = request.form.get("meta_description", "").strip()
        article.category_id = int(request.form["category_id"])
        article.is_published = request.form.get("is_published") == "on"
        article.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f"Article '{title}' updated.", "success")
        return redirect(url_for("kb.kb_admin_articles"))
    return render_template("admin/kb_article_edit.html", article=article, categories=categories)


@kb.route("/admin/kb/article/<int:article_id>/delete", methods=["POST"])
@login_required
def kb_delete_article(article_id):
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.main"))
    article = KBArticle.query.get_or_404(article_id)
    db.session.delete(article)
    db.session.commit()
    flash("Article deleted.", "success")
    return redirect(url_for("kb.kb_admin_articles"))


@kb.route("/admin/kb/categories")
@login_required
def kb_admin_categories():
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.main"))
    categories = KBCategory.query.order_by(KBCategory.display_order, KBCategory.name).all()
    return render_template("admin/kb_categories.html", categories=categories)


@kb.route("/admin/kb/category/create", methods=["POST"])
@login_required
def kb_create_category():
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.main"))
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name required.", "warning")
        return redirect(url_for("kb.kb_admin_categories"))
    slug = _unique_slug(_slugify(name), KBCategory)
    db.session.add(KBCategory(
        name=name,
        slug=slug,
        description=request.form.get("description", "").strip(),
        icon=request.form.get("icon", "book"),
        display_order=int(request.form.get("display_order", 0) or 0),
    ))
    db.session.commit()
    flash(f"Category '{name}' created.", "success")
    return redirect(url_for("kb.kb_admin_categories"))


@kb.route("/admin/kb/category/<int:cat_id>/edit", methods=["POST"])
@login_required
def kb_edit_category(cat_id):
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.main"))
    cat = KBCategory.query.get_or_404(cat_id)
    name = request.form.get("name", "").strip()
    if name and name != cat.name:
        cat.slug = _unique_slug(_slugify(name), KBCategory, exclude_id=cat.id)
        cat.name = name
    cat.description = request.form.get("description", cat.description or "")
    cat.icon = request.form.get("icon", cat.icon)
    cat.display_order = int(request.form.get("display_order", cat.display_order) or 0)
    cat.is_active = request.form.get("is_active") == "on"
    db.session.commit()
    flash(f"Category '{cat.name}' updated.", "success")
    return redirect(url_for("kb.kb_admin_categories"))


@kb.route("/admin/kb/category/<int:cat_id>/delete", methods=["POST"])
@login_required
def kb_delete_category(cat_id):
    if not current_user.is_admin():
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard.main"))
    cat = KBCategory.query.get_or_404(cat_id)
    if cat.articles.count() > 0:
        flash("Cannot delete a category that has articles. Move or delete articles first.", "warning")
        return redirect(url_for("kb.kb_admin_categories"))
    db.session.delete(cat)
    db.session.commit()
    flash(f"Category '{cat.name}' deleted.", "success")
    return redirect(url_for("kb.kb_admin_categories"))
