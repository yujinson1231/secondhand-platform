from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import update

from app.extensions import db
from app.models import User, Transaction
from app.forms import TransferForm

bp = Blueprint("transactions", __name__, url_prefix="/transfer")


@bp.route("", methods=["GET", "POST"])
@login_required
def transfer():
    form = TransferForm()
    if form.validate_on_submit():
        receiver_username = form.receiver_username.data.strip()
        amount = form.amount.data

        receiver = db.session.execute(
            db.select(User).filter_by(username=receiver_username)
        ).scalar_one_or_none()

        if receiver is None:
            flash("받는 사람을 찾을 수 없습니다.", "danger")
        elif receiver.id == current_user.id:
            flash("본인에게는 송금할 수 없습니다.", "danger")
        else:
            # Atomic conditional decrement: the WHERE clause re-checks the
            # balance at the database layer, in the same statement as the
            # decrement. This avoids the classic read-balance-then-write
            # race condition where two concurrent transfers could both pass
            # an application-level "balance >= amount" check and overdraw
            # the account.
            result = db.session.execute(
                update(User)
                .where(User.id == current_user.id, User.balance >= amount)
                .values(balance=User.balance - amount)
            )

            if result.rowcount == 0:
                db.session.rollback()
                flash("잔액이 부족합니다.", "danger")
            else:
                db.session.execute(
                    update(User)
                    .where(User.id == receiver.id)
                    .values(balance=User.balance + amount)
                )
                db.session.add(
                    Transaction(sender_id=current_user.id, receiver_id=receiver.id, amount=amount)
                )
                db.session.commit()
                flash(f"{receiver.username}님에게 {amount:,}포인트를 송금했습니다.", "success")
                return redirect(url_for("transactions.history"))

    return render_template("transactions/transfer.html", form=form)


@bp.route("/history")
@login_required
def history():
    sent = db.session.execute(
        db.select(Transaction)
        .filter_by(sender_id=current_user.id)
        .order_by(Transaction.created_at.desc())
    ).scalars().all()
    received = db.session.execute(
        db.select(Transaction)
        .filter_by(receiver_id=current_user.id)
        .order_by(Transaction.created_at.desc())
    ).scalars().all()
    return render_template("transactions/history.html", sent=sent, received=received)
