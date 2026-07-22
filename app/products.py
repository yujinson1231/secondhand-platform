import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Product
from app.forms import ProductForm

bp = Blueprint("products", __name__, url_prefix="/products")


def _save_product_image(file_storage):
    """Validate and persist an uploaded product image, returning its stored
    filename (never the user-supplied one) or None if no file was given."""
    if not file_storage or not file_storage.filename:
        return None

    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        abort(400, description="허용되지 않는 파일 형식입니다.")

    # Random server-generated name: prevents path traversal, overwrite of
    # other users' files, and execution of an uploaded script disguised
    # with an image extension (extension is still whitelisted above).
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_name)
    file_storage.save(dest)
    return stored_name


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = ProductForm()
    if form.validate_on_submit():
        image_filename = _save_product_image(form.image.data)
        product = Product(
            name=form.name.data.strip(),
            description=form.description.data.strip(),
            price=form.price.data,
            image_filename=image_filename,
            seller_id=current_user.id,
        )
        db.session.add(product)
        db.session.commit()
        flash("상품이 등록되었습니다.", "success")
        return redirect(url_for("products.detail", product_id=product.id))

    return render_template("products/new.html", form=form)


@bp.route("/<int:product_id>")
def detail(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    # Blocked products are only visible to their owner and admins, not the
    # general public, but we don't 404 for the owner so they can see why.
    if product.status != "active":
        if not current_user.is_authenticated or (
            current_user.id != product.seller_id and not current_user.is_admin
        ):
            abort(404)
    return render_template("products/detail.html", product=product)


@bp.route("/mine")
@login_required
def mine():
    products = db.session.execute(
        db.select(Product).filter_by(seller_id=current_user.id).order_by(Product.created_at.desc())
    ).scalars().all()
    return render_template("products/mine.html", products=products)


@bp.route("/<int:product_id>/delete", methods=["POST"])
@login_required
def delete(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    # Ownership check: only the seller (or an admin, via the admin panel)
    # may delete a listing — prevents IDOR-style deletion of others' items.
    if product.seller_id != current_user.id:
        abort(403)

    db.session.delete(product)
    db.session.commit()
    flash("상품이 삭제되었습니다.", "info")
    return redirect(url_for("products.mine"))
