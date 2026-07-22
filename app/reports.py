from flask import Blueprint, render_template, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Report, Product, User
from app.forms import ReportForm

bp = Blueprint("reports", __name__, url_prefix="/report")


def _report_count(target_type: str, target_id: int) -> int:
    return db.session.execute(
        db.select(db.func.count())
        .select_from(Report)
        .filter_by(target_type=target_type, target_id=target_id)
    ).scalar_one()


def _apply_threshold(target_type: str, target_id: int):
    threshold = current_app.config["REPORT_THRESHOLD"]
    count = _report_count(target_type, target_id)
    if count < threshold:
        return

    if target_type == "product":
        product = db.session.get(Product, target_id)
        if product and product.status == "active":
            product.status = "blocked"
            db.session.commit()
    elif target_type == "user":
        user = db.session.get(User, target_id)
        if user and user.status == "active" and not user.is_admin:
            user.status = "suspended"
            db.session.commit()


@bp.route("/product/<int:product_id>", methods=["GET", "POST"])
@login_required
def report_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    if product.seller_id == current_user.id:
        abort(400, description="본인 상품은 신고할 수 없습니다.")

    form = ReportForm()
    if form.validate_on_submit():
        report = Report(
            reporter_id=current_user.id,
            target_type="product",
            target_id=product_id,
            reason=form.reason.data.strip(),
        )
        db.session.add(report)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("이미 신고한 상품입니다.", "warning")
            return redirect(url_for("products.detail", product_id=product_id))

        _apply_threshold("product", product_id)
        flash("신고가 접수되었습니다.", "success")
        return redirect(url_for("products.detail", product_id=product_id))

    return render_template("reports/report_form.html", form=form, target_label=f"상품: {product.name}")


@bp.route("/user/<int:user_id>", methods=["GET", "POST"])
@login_required
def report_user(user_id):
    target = db.session.get(User, user_id)
    if target is None:
        abort(404)
    if target.id == current_user.id:
        abort(400, description="본인을 신고할 수 없습니다.")

    form = ReportForm()
    if form.validate_on_submit():
        report = Report(
            reporter_id=current_user.id,
            target_type="user",
            target_id=user_id,
            reason=form.reason.data.strip(),
        )
        db.session.add(report)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("이미 신고한 사용자입니다.", "warning")
            return redirect(url_for("main.index"))

        _apply_threshold("user", user_id)
        flash("신고가 접수되었습니다.", "success")
        return redirect(url_for("main.index"))

    return render_template("reports/report_form.html", form=form, target_label=f"사용자: {target.username}")
