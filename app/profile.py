from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User
from app.forms import BioForm, PasswordChangeForm

bp = Blueprint("profile", __name__)


@bp.route("/mypage", methods=["GET", "POST"])
@login_required
def mypage():
    bio_form = BioForm(bio=current_user.bio)
    password_form = PasswordChangeForm()
    return render_template("profile/mypage.html", bio_form=bio_form, password_form=password_form)


@bp.route("/mypage/bio", methods=["POST"])
@login_required
def update_bio():
    bio_form = BioForm()
    if bio_form.validate_on_submit():
        current_user.bio = (bio_form.bio.data or "").strip()
        db.session.commit()
        flash("소개글이 수정되었습니다.", "success")
    else:
        flash("소개글 수정에 실패했습니다.", "danger")
    return redirect(url_for("profile.mypage"))


@bp.route("/mypage/password", methods=["POST"])
@login_required
def update_password():
    password_form = PasswordChangeForm()
    if password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash("현재 비밀번호가 올바르지 않습니다.", "danger")
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash("비밀번호가 변경되었습니다.", "success")
    else:
        flash("비밀번호 변경에 실패했습니다.", "danger")
    return redirect(url_for("profile.mypage"))


@bp.route("/users/<int:user_id>")
def view_profile(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    return render_template("profile/view.html", profile_user=user)
