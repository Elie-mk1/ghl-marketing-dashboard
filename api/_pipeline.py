"""Shared code for the Vercel functions.

Runs the project's own fetch.py -> clean.py -> metrics.py (unchanged) in a temporary folder,
and keeps the latest *good* result in a small Redis store (Upstash, free) so the page can load it.
If any step or consistency check fails, nothing is saved and the last good numbers stay.
"""
import contextlib
import io
import json
import os
import runpy
import shutil
import tempfile
from datetime import datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the project folder
DATA_KEY = "dashboard:data"
LOCK_KEY = "dashboard:refresh-lock"
COOLDOWN_MINUTES = 5          # the button can pull from GoHighLevel at most once every 5 minutes
LOCK_SECONDS = 120            # only one update at a time


def redis(*command):
    """One Redis command over Upstash's REST API, e.g. redis("GET", "key")."""
    url = os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not (url and token):
        raise RuntimeError("Storage isn't connected: add Upstash Redis in the Vercel project's Storage tab.")
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=list(command), timeout=15)
    r.raise_for_status()
    return r.json().get("result")


def load():
    """The latest good numbers, or None if nothing has been saved yet."""
    raw = redis("GET", DATA_KEY)
    return json.loads(raw) if raw else None


def run_pipeline():
    """fetch -> clean -> metrics in a throwaway folder. Returns the new data or raises."""
    work = tempfile.mkdtemp()            # /tmp is the only writable place in a serverless function
    previous_dir = os.getcwd()
    log = io.StringIO()
    try:
        os.chdir(work)
        with contextlib.redirect_stdout(log):
            for script in ("fetch.py", "clean.py", "metrics.py"):
                try:
                    runpy.run_path(os.path.join(ROOT, script), run_name="__main__")
                except SystemExit as e:              # the scripts stop with sys.exit("reason")
                    if e.code not in (None, 0):
                        raise RuntimeError(f"{script} stopped: {e.code}") from None
        text = open("site/data.json").read()
        if "@" in text:                              # same safety rule as before: no emails published
            raise RuntimeError("Safety check failed: the numbers contain an '@'.")
        return json.loads(text)
    finally:
        os.chdir(previous_dir)
        shutil.rmtree(work, ignore_errors=True)      # the raw GoHighLevel data is deleted straight away
        print(log.getvalue()[-6000:])                # step-by-step log -> Vercel's function logs


def minutes_since(timestamp):
    then = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - then).total_seconds() / 60


def refresh(force=False):
    """Pull fresh numbers and save them. force=True skips the cooldown (used by the Monday schedule)."""
    current = load()
    if current and not force and minutes_since(current["updated"]) < COOLDOWN_MINUTES:
        return {"status": "recent", "updated": current["updated"]}
    if not redis("SET", LOCK_KEY, "1", "NX", "EX", str(LOCK_SECONDS)):
        return {"status": "busy"}
    try:
        data = run_pipeline()
        redis("SET", DATA_KEY, json.dumps(data))
        return {"status": "updated", "updated": data["updated"]}
    finally:
        redis("DEL", LOCK_KEY)


def send_json(handler, code, payload):
    body = json.dumps(payload).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")      # always the latest saved numbers
    handler.end_headers()
    handler.wfile.write(body)
