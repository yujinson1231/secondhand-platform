from flask import Blueprint, render_template, request

from app.extensions import db
from app.models import Product

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    q = request.args.get("q", "", type=str).strip()

    stmt = db.select(Product).filter_by(status="active").order_by(Product.created_at.desc())
    if q:
        # Parameterized via SQLAlchemy — safe from SQL injection.
        # Escape LIKE wildcards the user might type so search stays literal.
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.filter(Product.name.ilike(f"%{escaped}%", escape="\\"))

    products = db.session.execute(stmt).scalars().all()
    return render_template("main/index.html", products=products, q=q)
