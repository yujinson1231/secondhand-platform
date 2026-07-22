from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, limiter
from app.models import User
from app.forms import RegisterForm, LoginForm

from datetime import datetime, timezone, timedelta

bp = Blueprint("auth", __name__)

# A syntactically valid hash with no matching password, used to keep the
# login response time constant whether or not the username exists. This
# prevents timing-based user enumeration.
_DUMMY_HASH = generate_password_hash("dummy-password-for-timing-only")


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        existing = db.session.execute(
            db.select(User).filter_by(username=username)
        ).scalar_one_or_none()
        if existing is not None:
            flash("이미 사용 중인 아이디입니다.", "danger")
            return render_template("auth/register.html", form=form)

        user = User(username=username, bio="", balance=current_app.config["STARTING_BALANCE"])
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("회원가입이 완료되었습니다. 로그인해주세요.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        user = db.session.execute(
            db.select(User).filter_by(username=username)
        ).scalar_one_or_none()

        if user is None:
            check_password_hash(_DUMMY_HASH, form.password.data)
            flash("아이디 또는 비밀번호가 올바르지 않습니다.", "danger")
            return render_template("auth/login.html", form=form)
        
        # SQLite/SQLAlchemy round-trips DateTime columns as naive values
        # (tzinfo is dropped on save and never restored on load), so "now"
        # must also be naive here or Python can't compare the two at all.
        # This value still represents UTC, matching models.utcnow().
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if user.locked_until and user.locked_until > now:
            flash("로그인 시도가 너무 많아 계정이 잠시 잠겼습니다. 잠시 후 다시 시도하세요.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.check_password(form.password.data):
            user.failed_login_count += 1
            if user.failed_login_count >= 5:
                user.locked_until = now + timedelta(minutes=15)
            db.session.commit()
            flash("아이디 또는 비밀번호가 올바르지 않습니다.", "danger")
            return render_template("auth/login.html", form=form)

        if user.status != "active":
            flash("휴면 처리된 계정입니다. 관리자에게 문의하세요.", "danger")
            return render_template("auth/login.html", form=form)
    
        user.failed_login_count = 0
        user.locked_until = None
        session.permanent = True
        login_user(user)
        flash("로그인되었습니다.", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for("main.index"))
