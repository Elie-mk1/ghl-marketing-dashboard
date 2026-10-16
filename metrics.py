"""Phase 5: calculate every dashboard number, by source, and check they add up.

Input : raw/clean.json   (from clean.py)
Output: site/data.json   (numbers only - no names or emails - this is what gets published)
"""
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# the 8 stages in the order the dashboard shows them: in progress -> won -> dropped out
STAGE_ORDER = ["Qualified Opt In", "Booked call", "Follow Up", "Closed",
               "Disqualified", "Cancelled", "No Show", "Lost"]
FUNNEL_STEPS = ["Leads", "Opted in", "Booked a call", "Had the call", "Closed (won)"]
# Every source belongs to one channel group. Only "Paid ads" can be bought with ad budget,
# so only that group is ranked for the budget advice. Move a source by editing one line here.
CHANNEL_GROUPS = {
    "Facebook Ad": "Paid ads",
    "Instagram Ad": "Paid ads",
    "Billboard": "Paid ads",
    "Google Search": "Paid ads",        # assumption: paid Google Ads, not free search results
    "Cold Email": "Outbound",
    "LinkedIn Outreach": "Outbound",
    "Referral": "Organic",
    "Website Form": "Organic",
    "Webinar": "Organic",               # assumption: free content, not bought with ad budget
}
GROUPS = {   # display order + one-line meaning shown on the dashboard
    "Paid ads": "Bought with ad budget - these compete for next month's money",
    "Outbound": "Paid for with the sales team's time and tools, not ad budget",
    "Organic": "Free channels the agency grows over time",
    "Unclassified": "New or unknown sources - add them to CHANNEL_GROUPS in metrics.py",
}
PAID_GROUP = "Paid ads"
MIN_LEADS = 15                          # fewer than this = too small to judge

clean = json.load(open("raw/clean.json"))
leads, deals = clean["leads"], clean["deals"]
UNKNOWN = "Unknown source"

# ---------------------------------------------------------------- group by source
leads_by_source = Counter(l["source"] for l in leads)
deals_by_source = defaultdict(list)
for d in deals:
    deals_by_source[d["source"]].append(d)

# grouped (paid ads -> outbound -> organic -> unclassified), biggest source first inside each group
group_of = {s: CHANNEL_GROUPS.get(s, "Unclassified") for s in leads_by_source}
group_names = list(GROUPS)
sources = sorted(leads_by_source, key=lambda s: (group_names.index(group_of[s]), -leads_by_source[s]))

# ---------------------------------------------------------------- metrics per source
per_source = {}
for s in sources:
    n_leads = leads_by_source[s]
    ds = deals_by_source[s]

    # pipeline: how many deals sit in each of the 8 stages right now
    stages = {name: sum(1 for d in ds if d["stage"] == name) for name in STAGE_ORDER}

    # funnel: how many people REACHED each step (level 1..4); step 0 is all leads
    reached = [n_leads] + [sum(1 for d in ds if d["level"] >= step) for step in range(1, 5)]

    # conversion: share who made it from one step to the next
    conversion = [round(reached[i + 1] / reached[i], 3) if reached[i] else None for i in range(4)]

    won = sum(1 for d in ds if d["won"])
    revenue = sum(d["revenue"] for d in ds)
    valued_sales = sum(1 for d in ds if d["revenue"] > 0)

    per_source[s] = {
        "group": group_of[s],
        "leads": n_leads,
        "deals": len(ds),
        "not_in_pipeline": n_leads - len(ds),
        "stages": stages,
        "reached": reached,
        "conversion": conversion,
        "won": won,
        "win_rate": round(won / n_leads, 3),
        "revenue": revenue,
        "avg_sale": round(revenue / valued_sales) if valued_sales else 0,
        "revenue_per_lead": round(revenue / n_leads),
    }

# ---------------------------------------------------------------- budget advice
# every source is ranked - small ones are flagged, never hidden
for s in sources:
    per_source[s]["small_sample"] = per_source[s]["leads"] < MIN_LEADS
named = [s for s in sources if s != UNKNOWN]
ranked = sorted(named, key=lambda s: per_source[s]["revenue_per_lead"], reverse=True)
paid = [s for s in ranked if group_of[s] == PAID_GROUP]
small = [s for s in named if per_source[s]["small_sample"]]
total_won = sum(p["won"] for p in per_source.values())


def money(s):
    return f"${per_source[s]['revenue_per_lead']:,}"


if not paid:
    sys.exit("No source is in the 'Paid ads' group - check CHANNEL_GROUPS in metrics.py")
best, worst = paid[0], paid[-1]
b, w = per_source[best], per_source[worst]

if b["small_sample"]:
    headline = (f"{best} looks like the strongest paid ad channel ({money(best)} per lead), but from only "
                f"{b['leads']} leads. Test it with a small budget increase before moving big money.")
else:
    headline = (f"Put more of next month's budget into {best}: each lead has brought in "
                f"{money(best)}, the most of any paid ad channel.")

if w["won"] == 0:
    subline = (f"{worst} hasn't produced a single sale from {w['leads']} leads. "
               "Stop spending on it until that changes.")
else:
    subline = f"{worst} returned the least ({money(worst)} per lead), so cut it back first."

caution = f"Based on {total_won} sales in total, so one sale can change the order."
if small:
    caution += (f" {', '.join(small)} brought fewer than {MIN_LEADS} leads, so treat "
                f"{'its' if len(small) == 1 else 'their'} numbers as an early signal.")

unclassified = [s for s in named if group_of[s] == "Unclassified"]
if unclassified:
    caution += f" {', '.join(unclassified)} isn't assigned to a channel group yet, so it isn't ranked for ad budget."

advice = {"best": best, "worst": worst, "headline": headline, "subline": subline,
          "caution": caution, "ranked": ranked, "small_sample": small}

# ---------------------------------------------------------------- consistency checks
checks = []


def check(name, ok):
    checks.append({"check": name, "passed": bool(ok)})
    print(("PASS  " if ok else "FAIL  ") + name)


p = per_source.values()
check("Leads by source add up to total leads", sum(x["leads"] for x in p) == len(leads))
check("Deals by source add up to total deals", sum(x["deals"] for x in p) == len(deals))
check("Each source: the 8 stages add up to its deals",
      all(sum(x["stages"].values()) == x["deals"] for x in p))
check("Each source: leads in pipeline + not in pipeline = its leads",
      all(x["deals"] + x["not_in_pipeline"] == x["leads"] for x in p))
check("Each source: funnel never grows from one step to the next",
      all(all(a >= b for a, b in zip(x["reached"], x["reached"][1:])) for x in p))
check("Each source: last funnel step = won deals", all(x["reached"][4] == x["won"] for x in p))
check("Revenue by source adds up to total revenue",
      sum(x["revenue"] for x in p) == sum(d["revenue"] for d in deals))
check("Every source is in exactly one channel group",
      sorted(sources) == sorted(leads_by_source) and all(x["group"] in GROUPS for x in p))
check("Kept + removed = what GoHighLevel returned",
      clean["end"]["leads"] + sum(e["leads"] for e in clean["log"] if e["kind"] == "removed")
      == clean["start"]["leads"])

# ---------------------------------------------------------------- save (only if everything passed)
if not all(c["passed"] for c in checks):
    sys.exit("A check failed - not saving, so the dashboard keeps its last good numbers.")

Path("site").mkdir(exist_ok=True)
json.dump({
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "stages": STAGE_ORDER,
    "funnel_steps": FUNNEL_STEPS,
    "sources": sources,
    "groups": [{"name": g, "note": GROUPS[g]} for g in GROUPS if g in group_of.values()],
    "by_source": per_source,
    "advice": advice,
    "cleaning": {"start": clean["start"], "end": clean["end"],
                 "typical_sale": clean["typical_sale"], "log": clean["log"]},
    "checks": checks,
}, open("site/data.json", "w"), indent=2)

print(f"\n{advice['headline']}\n{advice['subline']}\n{advice['caution']}")
print("\nGroup     Source              Leads  Deals  Won  Revenue   Per lead")
for s in sources:
    x = per_source[s]
    print(f"{x['group']:9} {s:18} {x['leads']:6} {x['deals']:6} {x['won']:4}  ${x['revenue']:>8,}  ${x['revenue_per_lead']:>6,}")
print("\nSaved site/data.json")