from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, ChatMessage, dm_room_name

bp = Blueprint("chat", __name__, url_prefix="/chat")


@bp.route("/")
@login_required
def global_chat():
    history = db.session.execute(
        db.select(ChatMessage)
        .filter_by(room="global")
        .order_by(ChatMessage.created_at.desc())
        .limit(100)
    ).scalars().all()
    history.reverse()
    return render_template("chat/global.html", history=history, room="global")


@bp.route("/users")
@login_required
def user_list():
    users = db.session.execute(
        db.select(User).filter(User.id != current_user.id, User.status == "active").order_by(User.username)
    ).scalars().all()
    return render_template("chat/user_list.html", users=users)


@bp.route("/dm/<int:user_id>")
@login_required
def dm(user_id):
    other = db.session.get(User, user_id)
    if other is None or other.id == current_user.id:
        abort(404)

    room = dm_room_name(current_user.id, other.id)
    history = db.session.execute(
        db.select(ChatMessage).filter_by(room=room).order_by(ChatMessage.created_at.desc()).limit(100)
    ).scalars().all()
    history.reverse()
    return render_template("chat/dm.html", history=history, room=room, other=other)
