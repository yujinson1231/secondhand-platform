import os
from datetime import timezone, timedelta
from flask import Flask, render_template, request
from flask_login import current_user, logout_user

from config import Config
from app.extensions import db, login_manager, csrf, socketio, limiter

# All timestamps are stored in UTC (see models.utcnow) so the database is
# unambiguous no matter where the server runs. This offset is only used to
# render times in Korea Standard Time for display in templates.
KST = timezone(timedelta(hours=9))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "", 1)
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    @app.template_filter("kst")
    def format_kst(dt, fmt="%Y-%m-%d %H:%M"):
        # dt is a naive datetime that actually represents UTC (see
        # models.utcnow). We attach tzinfo=utc first so astimezone() knows
        # what it's converting from, then shift it to KST for display.
        if dt is None:
            return ""
        return dt.replace(tzinfo=timezone.utc).astimezone(KST).strftime(fmt)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    # No cors_allowed_origins is passed on purpose: Flask-SocketIO then
    # only accepts same-origin connections, which is what we want since
    # this app and its websocket endpoint are served from one origin.
    socketio.init_app(app, async_mode="threading")

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Defence in depth: if an already-logged-in session belongs to a user
    # who has since been suspended by an admin (or by the auto-suspend
    # logic), force them out on their very next request instead of waiting
    # for the session to expire.
    @app.before_request
    def enforce_active_session():
        if current_user.is_authenticated and current_user.status != "active":
            logout_user()

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; "
            "script-src 'self'; style-src 'self' 'unsafe-inline'"
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.products import bp as products_bp
    from app.chat import bp as chat_bp
    from app.reports import bp as reports_bp
    from app.transactions import bp as transactions_bp
    from app.profile import bp as profile_bp
    from app.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)

    from app import sockets  # noqa: F401  (registers socketio event handlers)

    @app.errorhandler(400)
    def bad_request(e):
        message = getattr(e, "description", None) or "잘못된 요청입니다."
        return render_template("errors/error.html", code=400, message=message), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/error.html", code=403, message="접근 권한이 없습니다."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/error.html", code=404, message="페이지를 찾을 수 없습니다."), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/error.html", code=413, message="업로드한 파일이 너무 큽니다."), 413

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/error.html", code=500, message="서버 오류가 발생했습니다."), 500

    with app.app_context():
        db.create_all()
        _seed_admin(app)

    return app


def _seed_admin(app):
    from app.models import User

    admin_password = app.config.get("ADMIN_PASSWORD")
    existing = db.session.execute(
        db.select(User).filter_by(username=app.config["ADMIN_USERNAME"])
    ).scalar_one_or_none()

    if existing is not None or not admin_password:
        return

    admin = User(
        username=app.config["ADMIN_USERNAME"],
        role="admin",
        status="active",
        balance=0,
        bio="관리자 계정",
    )
    admin.set_password(admin_password)
    db.session.add(admin)
    db.session.commit()
