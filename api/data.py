"""GET /api/data -> the latest good dashboard numbers (counts only, no personal details)."""
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pipeline import load, refresh, send_json  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            data = load()
            if data is None:                      # very first visit: nothing saved yet, build it now
                refresh(force=True)
                data = load()
            if data is None:
                return send_json(self, 503, {"error": "No numbers yet. Try again in a minute."})
            send_json(self, 200, data)
        except Exception as e:
            print(f"data error: {e}")
            send_json(self, 500, {"error": "Couldn't load the numbers right now."})
