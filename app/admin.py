from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, Product, Report, AuditLog
from app.decorators import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@login_required
@admin_required
def _guard():
    # Every route in this blueprint requires an authenticated admin.
    # Enforced server-side from the session-backed current_user, never
    # from any client-supplied field, so a regular user cannot simply
    # send role=admin to escalate privileges.
    pass


@bp.route("/")
def dashboard():
    stats = {
        "user_count": db.session.execute(db.select(db.func.count()).select_from(User)).scalar_one(),
        "product_count": db.session.execute(db.select(db.func.count()).select_from(Product)).scalar_one(),
        "report_count": db.session.execute(db.select(db.func.count()).select_from(Report)).scalar_one(),
    }
    return render_template("admin/dashboard.html", stats=stats)


@bp.route("/users")
def users():
    all_users = db.session.execute(db.select(User).order_by(User.id)).scalars().all()
    return render_template("admin/users.html", users=all_users)


@bp.route("/users/<int:user_id>/suspend", methods=["POST"])
def suspend_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.is_admin:
        abort(400, description="관리자 계정은 휴면 처리할 수 없습니다.")
    user.status = "suspended"
    db.session.add(AuditLog(
        actor_id=current_user.id,
        action="suspend_user",
        target_type="user",
        target_id=user.id,
    ))
    db.session.commit()
    flash(f"{user.username} 계정을 휴면 처리했습니다.", "info")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/activate", methods=["POST"])
def activate_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    user.status = "active"
    db.session.add(AuditLog(
        actor_id=current_user.id,
        action="activate_user",
        target_type="user",
        target_id=user.id,
    ))
    db.session.commit()
    flash(f"{user.username} 계정을 활성화했습니다.", "info")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.is_admin:
        abort(400, description="관리자 계정은 삭제할 수 없습니다.")
    if user.id == current_user.id:
        abort(400, description="본인 계정은 삭제할 수 없습니다.")
    db.session.add(AuditLog(
        actor_id=current_user.id,
        action="delete_user",
        target_type="user",
        target_id=user.id,
    ))
    db.session.delete(user)
    db.session.commit()
    flash(f"{user.username} 계정을 삭제했습니다.", "info")
    return redirect(url_for("admin.users"))


@bp.route("/products")
def products():
    all_products = db.session.execute(db.select(Product).order_by(Product.id.desc())).scalars().all()
    return render_template("admin/products.html", products=all_products)


@bp.route("/products/<int:product_id>/block", methods=["POST"])
def block_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    product.status = "blocked"
    db.session.add(AuditLog(
        actor_id=current_user.id,
        action="block_product",
        target_type="product",
        target_id=product.id,
    ))
    db.session.commit()
    flash(f"'{product.name}' 상품을 차단했습니다.", "info")
    return redirect(url_for("admin.products"))


@bp.route("/products/<int:product_id>/unblock", methods=["POST"])
def unblock_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    product.status = "active"
    db.session.add(AuditLog(
        actor_id=current_user.id,
        action="unblock_product",
        target_type="product",
        target_id=product.id,
    ))
    db.session.commit()
    flash(f"'{product.name}' 상품 차단을 해제했습니다.", "info")
    return redirect(url_for("admin.products"))


@bp.route("/products/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    db.session.add(AuditLog(
        actor_id=current_user.id,
        action="delete_product",
        target_type="product",
        target_id=product.id,
    ))
    db.session.delete(product)
    db.session.commit()
    flash(f"'{product.name}' 상품을 삭제했습니다.", "info")
    return redirect(url_for("admin.products"))


@bp.route("/reports")
def reports():
    all_reports = db.session.execute(db.select(Report).order_by(Report.created_at.desc())).scalars().all()

    # Resolve target labels for display without N+1-ing the templates.
    user_ids = {r.target_id for r in all_reports if r.target_type == "user"}
    product_ids = {r.target_id for r in all_reports if r.target_type == "product"}
    users_by_id = {
        u.id: u for u in db.session.execute(db.select(User).filter(User.id.in_(user_ids))).scalars()
    } if user_ids else {}
    products_by_id = {
        p.id: p for p in db.session.execute(db.select(Product).filter(Product.id.in_(product_ids))).scalars()
    } if product_ids else {}
    reporters_by_id = {
        u.id: u for u in db.session.execute(db.select(User)).scalars()
    }

    return render_template(
        "admin/reports.html",
        reports=all_reports,
        users_by_id=users_by_id,
        products_by_id=products_by_id,
        reporters_by_id=reporters_by_id,
    )

@bp.route("/audit-logs")
def audit_logs():
    logs = db.session.execute(
        db.select(AuditLog).order_by(AuditLog.created_at.desc())
    ).scalars().all()
    return render_template("admin/audit_logs.html", logs=logs)
