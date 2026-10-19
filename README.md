# Marketing Performance Dashboard

A one-page dashboard an agency owner opens on Monday morning to see **which lead source deserves next month's budget**. It pulls the agency's leads and 8-stage Sales Pipeline from GoHighLevel, cleans the data, and compares every source side by side.

**Live dashboard:** https://ghl-marketing-dashboard-rx.vercel.app/

## How it works

```
GoHighLevel API → fetch.py → clean.py → metrics.py → saved numbers → site/ (the web page)
                  download   clean +     numbers by     counts only,    reads them from
                  all data   log every   source +       kept in Redis   /api/data
                             change      9 checks
```
Hosted on **Vercel**. A small server function (`api/refresh.py`) runs the whole chain **every morning** and whenever the owner presses **"Get latest numbers"** (at most once every 5 minutes). If any check fails, nothing is saved and the last correct numbers stay online. GitHub Actions runs the same chain as a test on every code change.

| File | Job |
|---|---|
| `fetch.py` | Downloads all contacts, pipelines and deals from the GHL API (with pagination and retries). |
| `explore.py` | Profiles the raw data (tags, sources, dates, stages, values, duplicates). The cleaning rules were designed from this. |
| `clean.py` | Applies each data decision in order and logs how many leads/deals each step touched. |
| `metrics.py` | Calculates every number per source, runs 9 consistency checks, writes `site/data.json`. |
| `api/` | Vercel server functions: `refresh.py` runs the chain and saves the result, `data.py` serves the latest numbers to the page. The API key lives only here, in Vercel's settings. |
| `vercel.json` | Hosting settings and the daily schedule. |
| `site/` | The dashboard: HTML + CSS + JavaScript with Chart.js. It only reads `data.json`. |
| `decisions.md` | The full reasoning behind every rule. |

## Decisions and why

### Stack
- **Python scripts + static page + server functions on Vercel (free plan):** one place for the page, the scheduled update and the on-demand update, with a shareable link.
- **Data pulled server-side, never in the browser:** the API key lives in Vercel's encrypted settings; the page only ever receives counts.
- **Updates every morning (7–8 am Beirut), plus a "Get latest numbers" button:** the dashboard is never more than a day behind, a missed run costs one day instead of a week, and fresh numbers are one click away.
- **The button pulls from GoHighLevel at most once every 5 minutes, one update at a time:** nobody can flood the GHL API by clicking repeatedly.
- **The latest good numbers are kept in Upstash Redis (free):** server functions keep nothing between runs, so the page needs somewhere to read them from.
- **Started on GitHub Pages with hourly GitHub Actions, then moved:** GitHub ran the "hourly" schedule only every 2–5 hours, and a real refresh button needs a server to hold the key.
- **GitHub Actions still runs the full chain on every code change:** a change that breaks the cleaning or a check fails there before it reaches the owner.
- **A yellow warning appears if the numbers are more than 2 days old:** if the daily update ever stops, the owner sees it instead of trusting old numbers.
- **Only counts and totals are published:** no names, emails or other students' records, and an automatic check blocks any `@` from being published.
- **Read-only access to GHL:** the project never creates, edits or deletes anything in the shared sandbox.
- **Data cleanup shown as a one-line "About this data" note at the bottom, details on click:** the owner sees how many records were removed and why without the page turning into a work log.
- **Light and dark theme, switch at the top right:** starts from the computer's setting and remembers the owner's choice; charts redraw in the matching colors.

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
- **The advice is two short actions ("Increase spend on…", "Reduce spend on…"), with the numbers in the ranked board beside them:** an owner reads the decision in seconds, and the evidence is one glance away.

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
python -m http.server 8000 --directory site    # open http://localhost:8000 (reads site/data.json)
```
