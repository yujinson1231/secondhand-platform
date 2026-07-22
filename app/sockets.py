from datetime import timezone

import bleach
from flask_socketio import join_room, emit
from flask_login import current_user

from app.extensions import socketio, db
from app.models import ChatMessage
import time

# user_id -> (그 유저의 현재 10초 구간이 시작된 시각, 그 구간에서 보낸 메시지 수)
_rate_limit_state = {}

RATE_LIMIT_WINDOW_SECONDS = 10   # 몇 초 동안을 기준으로 볼지
RATE_LIMIT_MAX_MESSAGES = 5      # 그 시간 동안 최대 몇 개까지 허용할지


def _is_rate_limited(user_id):
    now = time.time()
    window_start, count = _rate_limit_state.get(user_id, (now, 0))

    if now - window_start > RATE_LIMIT_WINDOW_SECONDS:
        # 10초가 지났으면 새 구간 시작 (카운트 리셋)
        _rate_limit_state[user_id] = (now, 1)
        return False

    if count >= RATE_LIMIT_MAX_MESSAGES:
        return True  # 이미 5개 다 썼으니 차단

    _rate_limit_state[user_id] = (window_start, count + 1)
    return False


def _authorized_for_room(user_id: int, room: str) -> bool:
    """Server-side authorization for chat rooms: the client picks a room
    name, but we never trust it — global is open to any authenticated
    user, and a dm:<a>:<b> room may only be joined by user a or b. This
    stops one user from eavesdropping on or injecting into another pair's
    private conversation just by guessing/sending a room id."""
    if room == "global":
        return True
    if room.startswith("dm:"):
        parts = room.split(":")
        if len(parts) == 3:
            try:
                a, b = int(parts[1]), int(parts[2])
            except ValueError:
                return False
            return user_id in (a, b)
    return False


@socketio.on("join")
def handle_join(data):
    if not current_user.is_authenticated:
        return False
    room = (data or {}).get("room", "")
    if not _authorized_for_room(current_user.id, room):
        return False
    join_room(room)


@socketio.on("send_message")
def handle_send_message(data):
    if not current_user.is_authenticated:
        return False
    if _is_rate_limited(current_user.id):
        return False   # 조용히 무시 (메시지 저장도, 전송도 안 함)
    
    room = (data or {}).get("room", "")
    if not _authorized_for_room(current_user.id, room):
        return False

    raw_content = (data or {}).get("content", "")
    if not isinstance(raw_content, str):
        return False
    content = bleach.clean(raw_content.strip(), tags=[], attributes={}, strip=True)
    if not content or len(content) > 2000:
        return False

    message = ChatMessage(room=room, sender_id=current_user.id, content=content)
    db.session.add(message)
    db.session.commit()

    emit(
        "new_message",
        {
            "room": room,
            "sender": current_user.username,
            "sender_id": current_user.id,
            "content": content,
            # created_at is stored naive-but-UTC (see models.utcnow); mark
            # it explicitly as UTC here so the browser's `new Date(...)`
            # parses it correctly and converts it to the viewer's local
            # time zone itself, instead of misreading raw UTC numbers as
            # if they were already local time.
            "created_at": message.created_at.replace(tzinfo=timezone.utc).isoformat(),
        },
        room=room,
    )
