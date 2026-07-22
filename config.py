import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is not set. Copy .env.example to .env and set a random SECRET_KEY."
        )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session / cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"

    # File upload limits (also enforced per-field, this is a hard cap for the whole request)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

    UPLOAD_FOLDER = os.path.join(basedir, "app", "static", "uploads")
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

    STARTING_BALANCE = int(os.environ.get("STARTING_BALANCE", "100000"))
    REPORT_THRESHOLD = int(os.environ.get("REPORT_THRESHOLD", "3"))

    WTF_CSRF_TIME_LIMIT = None
