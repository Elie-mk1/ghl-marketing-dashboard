import json, re
from collections import Counter, defaultdict

data = json.load(open("raw/ghl_raw.json"))
contacts = data["contacts"]
opps = data["opportunities"]
pipelines = data["pipelines"]

def show(title, counter, top=30):
    print(f"\n=== {title} ===")
    for value, n in counter.most_common(top):
        print(f"  {n:4}  {value}")

# ---------- 1. WHO IS IN THIS SANDBOX? ----------
show("Tags on contacts", Counter(t for c in contacts for t in (c.get("tags") or [])))
show("Contact sources", Counter(str(c.get("source")) for c in contacts))
show("Day each contact was created", Counter((c.get("dateAdded") or "")[:10] for c in contacts))
show("Email domains", Counter((c.get("email") or "NO EMAIL").split("@")[-1] for c in contacts))

# ---------- 2. COMPARE GROUPS: pick a tag and look at who has it vs who doesn't ----------
TAG = "dash-project"   # try other tags from section 1 too
has = [c for c in contacts if TAG in (c.get("tags") or [])]
hasnt = [c for c in contacts if TAG not in (c.get("tags") or [])]
print(f"\n=== Contacts WITH tag '{TAG}': {len(has)} | WITHOUT: {len(hasnt)} ===")
show(f"Sources WITH '{TAG}'", Counter(str(c.get("source")) for c in has))
show(f"Sources WITHOUT '{TAG}'", Counter(str(c.get("source")) for c in hasnt))
show(f"Tags on contacts WITHOUT '{TAG}'", Counter(t for c in hasnt for t in (c.get("tags") or [])))

# ---------- 3. DEALS PER PIPELINE ----------
pipe_name = {p["id"]: p["name"] for p in pipelines}
show("Deals per pipeline", Counter(pipe_name.get(o["pipelineId"], "?") for o in opps))

# ---------- 4. SALES PIPELINE: stage vs status ----------
sales = next(p for p in pipelines if p["name"] == "Sales Pipeline")
stage_name = {s["id"]: s["name"] for s in sales["stages"]}
sales_opps = [o for o in opps if o["pipelineId"] == sales["id"]]
show("Sales Pipeline: stage / status", Counter(
    f"{stage_name.get(o['pipelineStageId'], '?'):18} / {o.get('status')}" for o in sales_opps))

# ---------- 5. DEAL VALUES ----------
values = defaultdict(list)
for o in sales_opps:
    values[f"{stage_name.get(o['pipelineStageId'])} / {o.get('status')}"].append(o.get("monetaryValue"))
print("\n=== Deal values by stage/status (sorted) ===")
for key, vals in values.items():
    print(f"  {key}: {sorted(v for v in vals if v is not None)}")

# ---------- 6. DUPLICATE PEOPLE ----------
def full_name(c):
    return f"{c.get('firstName') or ''} {c.get('lastName') or ''}".strip().lower()

show("Emails used more than once", Counter(
    (c.get("email") or "").lower() for c in contacts if c.get("email")), top=5)
by_name = defaultdict(list)
for c in contacts:
    by_name[full_name(c)].append(c)
print("\n=== Names that appear more than once (compare the details!) ===")
for name, group in by_name.items():
    if len(group) > 1 and name:
        print(f"\n  {name}")
        for c in group:
            print(f"     email={c.get('email')}  company={c.get('companyName')}  "
                  f"city={c.get('city')}  source={c.get('source')}  tags={c.get('tags')}  "
                  f"added={c.get('dateAdded')}")

# ---------- 7. DEALS PER PERSON ----------
per_contact = Counter(o.get("contactId") for o in sales_opps)
show("How many deals each contact has (deals: number of contacts)", Counter(per_contact.values()))
# ---------- 8. QUICK CHECKS ON THE AGENCY GROUP ----------
agency_ids = {c["id"] for c in contacts if "dash-project" in (c.get("tags") or [])}
internal_ids = {c["id"] for c in contacts if "internal" in (c.get("tags") or [])}
copy_ids = {c["id"] for c in contacts if c["id"] in agency_ids
            and re.search(r"\.\d+@", c.get("email") or "")}

agency_opps = [o for o in sales_opps if o["contactId"] in agency_ids]
print("\nAgency deals in Sales Pipeline:", len(agency_opps))
print("Deals belonging to internal contacts:", sum(o["contactId"] in internal_ids for o in agency_opps))
print("Deals belonging to '.2' copies:", sum(o["contactId"] in copy_ids for o in agency_opps))
print("Disqualified/won deals that are the agency's:", sum(
    1 for o in agency_opps
    if stage_name.get(o["pipelineStageId"]) == "Disqualified" and o.get("status") == "won"))
won_vals = sorted(o.get("monetaryValue") for o in agency_opps
                  if stage_name.get(o["pipelineStageId"]) == "Closed")
print("Agency Closed deal values:", won_vals)