import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV", "development") != "production"
    # host=0.0.0.0 so the app is reachable from other devices on the same
    # network (e.g. testing from a phone), not just from this machine.
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug)
