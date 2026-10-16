# Marketing Performance Dashboard

A one-page dashboard an agency owner opens on Monday morning to see **which lead source deserves next month's budget**. It pulls the agency's leads and 8-stage Sales Pipeline from GoHighLevel, cleans the data, and compares every source side by side.

**Live dashboard:** https://elie-mk1.github.io/ghl-marketing-dashboard/

## How it works

```
GoHighLevel API → fetch.py → clean.py → metrics.py → site/data.json → site/ (GitHub Pages)
                  download   clean +     numbers by     counts only,     the web page
                  all data   log every   source +       no personal
                             change      9 checks       details
```
GitHub Actions runs the whole chain **every hour (at :17 past)**, on every code push, and on demand ("Run workflow"). If any check fails, nothing is published and the last correct dashboard stays online.

| File | Job |
|---|---|
| `fetch.py` | Downloads all contacts, pipelines and deals from the GHL API (with pagination and retries). |
| `explore.py` | Profiles the raw data (tags, sources, dates, stages, values, duplicates). The cleaning rules were designed from this. |
| `clean.py` | Applies each data decision in order and logs how many leads/deals each step touched. |
| `metrics.py` | Calculates every number per source, runs 9 consistency checks, writes `site/data.json`. |
| `site/` | The dashboard: HTML + CSS + JavaScript with Chart.js. It only reads `data.json`. |
| `decisions.md` | The full reasoning behind every rule. |

## Decisions and why

### Stack
- **Python scripts + static web page on GitHub Pages:** free, always on, a shareable link, nothing to maintain.
- **Data pulled server-side by GitHub Actions, not in the browser:** the API key never reaches browser code.
- **Hourly scheduled refresh, not live:** fresh enough to act on the same day, and the key stays server-side.
- **A countdown shows when the next update lands, and a "Check for new numbers" button loads it:** the owner can act on current numbers without waiting or guessing.
- **No "pull from GoHighLevel now" button in the page:** starting a refresh needs a GitHub token, and keys never go in browser code. That would need a small server holding the token.
- **A yellow warning appears if the numbers are more than 3 hours old:** if the hourly update ever stops, the owner sees it instead of trusting old numbers.
- **Only counts and totals are published:** no names, emails or other students' records, and an automatic check blocks any `@` from being published.
- **Read-only access to GHL:** the project never creates, edits or deletes anything in the shared sandbox.

### Which records belong to the agency
- **Only leads tagged `dash-project` are kept (49 removed):** that tag marks the one batch that is the agency's campaign. The rest is sandbox demo data or other students' projects.
- **Only the Sales Pipeline is used (11 deals removed):** the other 5 pipelines belong to other users.
- **Scope is decided by the lead, not the pipeline:** filtering by pipeline alone would drop ~90 leads that never became deals (hiding real drop-off) and let in 33 demo-data deals.
- **Deals follow their lead (33 deals removed):** if a lead is excluded, so is its deal.

### Data quality
- **Leads tagged `internal` removed (15):** the agency's own staff, not prospects.
- **Duplicates matched on same email OR same name + same company (12 removed):** the copies had altered emails (`name.12.2@…`), so email matching alone found nothing.
- **Never match on name alone:** 4 names appear twice but at different companies, so they are different people.
- **The original record is kept (first-touch attribution):** 11 of 12 copies had a different source, which would have credited one person to two channels.
- **"Closed" = won:** every Closed deal has status won.
- **A sale counts only if it's in Closed and not marked lost:** stage/status contradictions aren't counted as revenue (0 agency deals affected today; the rule protects future data).
- **Won deals with $0 or more than 10× the typical sale are left out of revenue but still count as wins (3 deals):** two $145,000 values would have inflated revenue 2.5×.
- **The median is used as the "typical sale":** outliers don't distort it the way they distort an average.
- **Blank sources become "Unknown source", never deleted:** nothing disappears from the totals (0 today).

### Metrics
- **Funnel follows the real sales path:** Leads → Opted in → Booked a call → Had the call → Closed. GHL's 8 stages aren't a straight line.
- **Exit stages count as reaching the step where they happened:** Disqualified = opted in; Cancelled/No Show = booked; Lost = had the call.
- **The pipeline chart shows all 8 stages** grouped as in progress (blue), won (green) and dropped out (grey); each bar sums to that source's deals.
- **Budget advice ranks by revenue per lead:** there's no ad-spend data, so this is the best proxy for return.
- **Sources are grouped into Paid ads, Outbound and Organic:** the owner's question is where to put *ad* money, so channels that can be bought with ads are shown apart from the rest.
- **Groups are labels, never totals:** every source keeps its own row and bar; summing a group would be the "blended number" the brief rules out.
- **Only the Paid ads group is ranked for the budget advice:** Outbound costs the sales team's time, and Organic can't be bought with ads.
- **Channels within 10% of each other are called a tie:** with 28 sales, a $5 gap (Instagram Ad $1,086 vs Billboard $1,081 per lead) isn't a real difference, so the advice says "grow both" instead of picking one.
- **Google Search counts as Paid ads; Webinar counts as Organic:** the data doesn't say which they are, so these are stated assumptions, changeable in one line (`CHANNEL_GROUPS` in `metrics.py`).
- **A source missing from the grouping shows as "Unclassified":** it is still displayed, but not ranked for ad budget until someone assigns it.
- **Every source is ranked; sources under 15 leads are flagged, never hidden:** the owner should still see a small channel that isn't paying off.
- **A caution shows when sales are few (28 total):** one sale can change the ranking.

### Consistency checks (publishing stops if any fail)
Leads and deals by source add up to totals; each source's 8 stages add up to its deals; pipeline + not-in-pipeline = leads; the funnel never grows; last funnel step = won deals; revenue adds up; every source is in exactly one channel group; kept + removed = what GHL returned.

## Limitations
- **No ad-spend data,** so true ROI and cost per lead can't be calculated.
- **The whole campaign was imported on one day,** so dates can't show trends over the 3 months.
- **Channel groups are assumptions:** Google Search could be free search traffic and Webinar could be promoted with ads.
- **Small numbers:** Instagram Ad ($1,086/lead) and Billboard ($1,081/lead) are effectively tied.

## Run it locally
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# put GHL_API_KEY and GHL_LOCATION_ID in a .env file
python fetch.py && python clean.py && python metrics.py
python -m http.server 8000 --directory site    # open http://localhost:8000
```
