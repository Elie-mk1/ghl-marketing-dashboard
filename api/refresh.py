"""Pull fresh numbers from GoHighLevel.

POST /api/refresh  -> the "Get latest numbers" button (at most once every 5 minutes)
GET  /api/refresh  -> Vercel's Monday schedule; only accepted with the CRON_SECRET Vercel sends
"""
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pipeline import refresh, send_json  # noqa: E402


def run(handler, force):
    try:
        result = refresh(force=force)
        send_json(handler, 200, result)
    except Exception as e:                    # GoHighLevel down, a check failed, ... -> keep old numbers
        print(f"refresh failed: {e}")
        send_json(handler, 500, {"status": "failed"})


class handler(BaseHTTPRequestHandler):
    def do_POST(self):                        # the button
        run(self, force=False)

    def do_GET(self):                         # the schedule
        secret = os.getenv("CRON_SECRET")
        if not secret or self.headers.get("Authorization") != f"Bearer {secret}":
            return send_json(self, 401, {"status": "unauthorized"})
        run(self, force=True)
