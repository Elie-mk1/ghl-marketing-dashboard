"""Phase 4: clean the raw GHL data, one decision per step.

Input : raw/ghl_raw.json   (from fetch.py)
Output: raw/clean.json     (clean leads + deals + a log of every change)
"""
import json
import re
import statistics

# ---------------------------------------------------------------- settings
AGENCY_TAG = "dash-project"                       # decision 1
PIPELINE_NAME = "Sales Pipeline"                  # decision 2
INTERNAL_TAGS = {"internal", "staff", "test"}     # decision 4
UNKNOWN_SOURCE = "Unknown source"                 # decision 10
OUTLIER_MULTIPLE = 10                             # decision 9: more than 10x a typical sale

# decision 11: what each stage means. level = how far along the path the deal got
#   1 = opted in, 2 = booked a call, 3 = had the call, 4 = closed (won)
STAGES = {
    "Qualified Opt In": {"group": "in progress", "level": 1},
    "Booked call":      {"group": "in progress", "level": 2},
    "Follow Up":        {"group": "in progress", "level": 3},
    "Closed":           {"group": "won",         "level": 4},
    "Disqualified":     {"group": "dropped out", "level": 1},
    "Cancelled":        {"group": "dropped out", "level": 2},
    "No Show":          {"group": "dropped out", "level": 2},
    "Lost":             {"group": "dropped out", "level": 3},
}

# ---------------------------------------------------------------- load
data = json.load(open("raw/ghl_raw.json"))
contacts = data["contacts"]
deals = data["opportunities"]
pipelines = data["pipelines"]
START_LEADS, START_DEALS = len(contacts), len(deals)

log = []  # every change goes here


def record(kind, title, why, leads=0, deals=0):
    """kind: 'removed', 'fixed' or 'flagged'."""
    log.append({"kind": kind, "title": title, "why": why, "leads": leads, "deals": deals})
    print(f"[{kind:7}] {title}: {leads} leads, {deals} deals")


def tags_of(c):
    return {t.strip().lower() for t in (c.get("tags") or [])}


# ---------------------------------------------------------------- step 1: other pipelines
sales = next(p for p in pipelines if p["name"] == PIPELINE_NAME)
stage_name = {s["id"]: s["name"] for s in sales["stages"]}
other_pipeline = [d for d in deals if d["pipelineId"] != sales["id"]]
deals = [d for d in deals if d["pipelineId"] == sales["id"]]
record("removed", "Deals in other pipelines",
       f"Only the agency's '{PIPELINE_NAME}' counts; the others belong to other users.",
       deals=len(other_pipeline))

# ---------------------------------------------------------------- step 2: not the agency's leads
removed_lead_ids = {}  # contact id -> why it was removed (deals follow their lead later)
outsiders = [c for c in contacts if AGENCY_TAG not in tags_of(c)]
for c in outsiders:
    removed_lead_ids[c["id"]] = "Leads that aren't this agency's"
contacts = [c for c in contacts if AGENCY_TAG in tags_of(c)]
record("removed", "Leads that aren't this agency's",
       f"The sandbox is shared. The agency's campaign is the batch tagged '{AGENCY_TAG}'; "
       "everything else is demo data or other students' work.",
       leads=len(outsiders))

# ---------------------------------------------------------------- step 3: internal / staff
internal = [c for c in contacts if tags_of(c) & INTERNAL_TAGS]
for c in internal:
    removed_lead_ids[c["id"]] = "Internal & test leads"
contacts = [c for c in contacts if not tags_of(c) & INTERNAL_TAGS]
record("removed", "Internal & test leads",
       "The agency's own staff and test records, not prospects.", leads=len(internal))


# ---------------------------------------------------------------- step 4: duplicate people
def is_copy(c):
    """True for emails like name.12.2@example.com (a copied record)."""
    return bool(re.search(r"\.\d+@", c.get("email") or ""))


def match_keys(c):
    """Ways to recognise the same person: same email, or same name AND same company."""
    keys = []
    email = (c.get("email") or "").strip().lower()
    if email:
        keys.append("email:" + email)
    name = f"{c.get('firstName') or ''} {c.get('lastName') or ''}".strip().lower()
    company = (c.get("companyName") or "").strip().lower()
    if name and company:  # decision 6: never name alone
        keys.append(f"person:{name}|{company}")
    return keys


# earliest first; on a tie, the original before the '.2' copy (decision 5: first touch)
contacts.sort(key=lambda c: (c.get("dateAdded") or "", is_copy(c)))
seen = {}           # key -> id of the record we kept
original_of = {}    # id of any record -> id of the kept original
kept, duplicates = [], 0
for c in contacts:
    match = next((seen[k] for k in match_keys(c) if k in seen), None)
    if match:
        original_of[c["id"]] = match
        duplicates += 1
        original = next(x for x in kept if x["id"] == match)
        if not original.get("source") and c.get("source"):
            original["source"] = c["source"]  # recover a blank source from the copy
    else:
        original_of[c["id"]] = c["id"]
        kept.append(c)
        for k in match_keys(c):
            seen[k] = c["id"]
contacts = kept
record("removed", "Duplicate leads",
       "The same person entered twice (same email, or same name at the same company). "
       "Kept the original so the channel that first brought them in gets the credit.",
       leads=duplicates)

# ---------------------------------------------------------------- step 5: deals follow their lead
kept_deals, removed_with_lead, orphans = [], 0, 0
for d in deals:
    cid = d.get("contactId")
    if cid in original_of:
        d["contactId"] = original_of[cid]  # a copy's deal moves to the original person
        kept_deals.append(d)
    elif cid in removed_lead_ids:
        removed_with_lead += 1
    else:
        orphans += 1
record("removed", "Deals of removed leads",
       "A deal goes wherever its lead went (other users' or internal leads).",
       deals=removed_with_lead)
record("removed", "Deals with no lead attached",
       "The deal points to a contact that doesn't exist, so its source is unknown.", deals=orphans)

# one deal per person: keep the one that got furthest
best = {}
for d in kept_deals:
    level = STAGES.get(stage_name.get(d["pipelineStageId"]), {"level": 0})["level"]
    cur = best.get(d["contactId"])
    if cur is None or level > cur[0]:
        best[d["contactId"]] = (level, d)
record("removed", "Duplicate deals",
       "The same person had more than one deal; kept the furthest along.",
       deals=len(kept_deals) - len(best))
deals = [d for _, d in best.values()]

# ---------------------------------------------------------------- step 6: sources
lead_source = {}
unknown = 0
for c in contacts:
    s = (c.get("source") or "").strip()
    if not s or s.lower() in ("none", "null", "unknown"):
        s = UNKNOWN_SOURCE
        unknown += 1
    lead_source[c["id"]] = s
record("flagged", "Leads with no source",
       f"Kept as '{UNKNOWN_SOURCE}' so nothing disappears, but no advice is based on them.",
       leads=unknown)

# ---------------------------------------------------------------- step 7: stage + won status
contradictions = 0
clean_deals = []
for d in deals:
    stage = stage_name.get(d["pipelineStageId"], "?")
    info = STAGES.get(stage, {"group": "dropped out", "level": 1})
    status = (d.get("status") or "open").lower()
    won = stage == "Closed" and status not in ("lost", "abandoned")       # decision 8
    if status == "won" and not won:
        contradictions += 1
    level = info["level"]
    if stage == "Closed" and not won:
        level = 3  # in Closed but marked lost: they had the call, but didn't buy
    clean_deals.append({"id": d["id"], "contact_id": d["contactId"], "stage": stage,
                        "group": info["group"], "level": level,
                        "won": won, "value": d.get("monetaryValue")})
record("flagged", "Marked 'won' but not in Closed",
       "Stage and status contradict each other, so it is not counted as a sale.",
       deals=contradictions)

# ---------------------------------------------------------------- step 8: untrustworthy values
won_values = [d["value"] for d in clean_deals if d["won"] and (d["value"] or 0) > 0]
typical = statistics.median(won_values) if won_values else 0
untrusted = 0
for d in clean_deals:
    d["revenue"] = 0
    if not d["won"]:
        continue
    v = d["value"] or 0
    if v <= 0 or v > OUTLIER_MULTIPLE * typical:
        untrusted += 1  # still a win, but its value is left out of revenue
    else:
        d["revenue"] = v
record("flagged", "Won deals with values we can't trust",
       f"A typical sale is ${typical:,.0f}. $0 or more than {OUTLIER_MULTIPLE}x typical is left out "
       "of revenue; the deal still counts as won.", deals=untrusted)

# ---------------------------------------------------------------- save + self-check
for d in clean_deals:
    d["source"] = lead_source[d["contact_id"]]
removed_leads = sum(e["leads"] for e in log if e["kind"] == "removed")
removed_deals = sum(e["deals"] for e in log if e["kind"] == "removed")
assert len(contacts) + removed_leads == START_LEADS, "some leads went missing!"
assert len(clean_deals) + removed_deals == START_DEALS, "some deals went missing!"

json.dump({
    "start": {"leads": START_LEADS, "deals": START_DEALS},
    "end": {"leads": len(contacts), "deals": len(clean_deals)},
    "typical_sale": typical,
    "leads": [{"id": c["id"], "source": lead_source[c["id"]]} for c in contacts],
    "deals": clean_deals,
    "log": log,
}, open("raw/clean.json", "w"), indent=2)
print(f"\n{START_LEADS} -> {len(contacts)} leads, {START_DEALS} -> {len(clean_deals)} deals. "
      f"Typical sale ${typical:,.0f}. Saved raw/clean.json")
