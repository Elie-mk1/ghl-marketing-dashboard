import os, json, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GHL_API_KEY")
LOCATION_ID = os.getenv("GHL_LOCATION_ID")
BASE_URL = "https://services.leadconnectorhq.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Version": "2021-07-28",
    "Accept": "application/json",
    "User-Agent": "ghl-dashboard-learning",
}
PAGE_SIZE = 100


def get(path, params):
    """Call the API. If GHL says 'too many requests' or has a hiccup, wait and retry."""
    for attempt in range(5):
        r = requests.get(BASE_URL + path, headers=HEADERS, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503):
            wait = 2 ** attempt               # wait 1s, 2s, 4s, 8s... ("exponential backoff")
            print(f"  got {r.status_code}, retrying in {wait}s")
            time.sleep(wait)
            continue
        raise SystemExit(f"Error {r.status_code}: {r.text}")   # any other error: stop loudly
    raise SystemExit("Gave up after 5 attempts")


def fetch_pipelines():
    return get("/opportunities/pipelines", {"locationId": LOCATION_ID})["pipelines"]


def fetch_contacts():
    """Cursor pagination: keep asking for 'the page after the last record I got'."""
    all_contacts = []
    params = {"locationId": LOCATION_ID, "limit": PAGE_SIZE}
    while True:
        data = get("/contacts/", params)
        page = data["contacts"]
        all_contacts.extend(page)
        print(f"  contacts so far: {len(all_contacts)}")
        if len(page) < PAGE_SIZE:            # a short page means it was the last one
            break
        params["startAfterId"] = data["meta"]["startAfterId"]   # the bookmark
        params["startAfter"] = data["meta"]["startAfter"]
    return all_contacts


def fetch_opportunities():
    """Page-number pagination: page 1, 2, 3... until a page is short."""
    all_opps = []
    page_number = 1
    while True:
        data = get("/opportunities/search",
                   {"location_id": LOCATION_ID, "limit": PAGE_SIZE, "page": page_number})
        page = data["opportunities"]
        all_opps.extend(page)
        print(f"  opportunities so far: {len(all_opps)}")
        if len(page) < PAGE_SIZE:
            break
        page_number += 1
    return all_opps


if __name__ == "__main__":
    print("Fetching pipelines...")
    pipelines = fetch_pipelines()
    print("Fetching contacts...")
    contacts = fetch_contacts()
    print("Fetching opportunities...")
    opportunities = fetch_opportunities()

    Path("raw").mkdir(exist_ok=True)          # create the raw/ folder if missing
    with open("raw/ghl_raw.json", "w") as f:
        json.dump({"pipelines": pipelines, "contacts": contacts,
                   "opportunities": opportunities}, f, indent=2)
    print(f"\nSaved {len(contacts)} contacts, {len(opportunities)} opportunities, "
          f"{len(pipelines)} pipelines to raw/ghl_raw.json")