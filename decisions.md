## Problem: (what you found, with the numbers)
Decision: (what you'll do about it)
Why: (the business reason)
Scope is decided by the lead (agency tag), not by the pipeline. Filtering by pipeline would drop the ~117 leads who never became deals (inflating conversion) and would let in ~33 demo-data deals that share the pipeline.
# Data decisions

## 1. Shared sandbox: other users' leads
Found: 370 contacts. 321 tagged `dash-project` (one batch, 2026-09-04, 9 sources).
49 others: 32 `demo-data`/`sandbox`, ~17 from other students (q:, sg-, website-booking...).
Decision: Keep only contacts tagged `dash-project`. Remove the other 49.
Why: The tagged group is the only one that looks like one coherent campaign: same batch,
same 9 marketing sources. The rest are other users' tests or generic demo data, with
different tags, sources and October dates. Counting them would mix other people's
experiments into the agency's results.

## 2. Other pipelines
Found: 11 deals in 4 other pipelines.
Decision: Use only deals in the "Sales Pipeline".
Why: The brief names the agency's 8-stage Sales Pipeline. The other pipelines have
different stages and belong to other students' projects.

## 3. Scope by lead, not by pipeline
Found: Sales Pipeline has 237 deals, only 204 are the agency's. ~117 agency leads have no deal.
Decision: Decide scope by the lead (agency tag). Keep a deal only if it is in the Sales
Pipeline AND belongs to a kept lead. Leads with no deal stay in the lead counts.
Why: Filtering by pipeline alone would (a) drop the ~117 leads who never became deals,
making every source look like it converts ~100% (survivorship bias), and (b) let in
33 demo-data deals that share the pipeline.

## 4. Internal / staff leads
Found: 15 agency leads tagged `internal` (0 deals).
Decision: Remove them.
Why: They are the agency's own staff, not prospects. Leaving them in inflates each
source's lead volume and lowers its conversion rate with people who were never buyers.

## 5. Duplicate people
Found: 12 pairs, same name + company, email with `.2`, created ~1 min later,
11 of 12 with a different source. 0 deals on the copies. No repeated emails.
Decision: Treat same name + same company as the same person. Keep the original
(earliest record, without `.2`) and its source; remove the copy.
Why: Otherwise one person is counted twice and credited to two channels, adding a fake
non-converting lead to the copy's source. Keeping the earliest record follows
first-touch attribution: the channel that first brought the person in gets the credit.
Email matching alone found nothing, because the copies have altered emails.

## 6. Same name, different person
Found: 4 names appear in both dash-project and demo-data with different companies.
Decision: Do not match duplicates on name alone; require name + company (or same email/phone).
Why: Two different people can share a name. Merging them would delete a real lead.

## 7. "Closed" means won
Found: all 28 Closed deals have status `won`.
Decision: Treat "Closed" as the sale stage (closed-won).
Why: In sales, "closing" means getting the customer to buy, and the data confirms it:
every Closed deal is marked won.

## 8. Stage/status contradictions
Found: 4 deals "won" but in Disqualified (all non-agency, 0 agency).
Decision: A deal counts as a sale only if it is in Closed and not marked lost/abandoned.
Keep the rule even though it affects 0 agency deals today.
Why: When two fields disagree, take the conservative reading rather than invent revenue.
The automation runs daily, so the rule protects future data.

## 9. Suspicious deal values
Found: typical sale $8,500 (range $1,500–12,000). Two agency sales of $145,000
and one of $0. Real revenue $190,750; with them $480,750.
Decision: Keep these deals as wins but leave their values out of revenue
(rule: $0 or less, or more than 10x the typical sale).
Why: The sales happened, but the numbers can't be trusted. $145,000 is 17x typical and
would inflate revenue 2.5x and push budget toward whichever sources got the fake values.
Deleting the whole deal would wrongly lower the win rate.

## 10. Missing sources
Found: 8 contacts with no source, all non-agency. 0 in the agency's data.
Decision: Try to recover a blank source from a duplicate or the lead's deal; otherwise
group it as "Unknown source". Never delete it, and never base budget advice on it.
Why: Nothing should silently disappear from the totals. The rule protects against
blanks appearing in future data.

## 11. Non-linear pipeline
Found: 8 stages = 3 forward + Closed (won) + 4 exits (Disqualified, Cancelled, No Show, Lost).
Decision: Build the funnel on the real path: Leads → Opted in → Booked a call →
Had the call → Closed. Each exit counts as reaching the step where it happened
(Disqualified = opted in; Cancelled / No Show = booked; Lost = had the call).
The stage chart still shows all 8 stages, grouped as in progress / won / dropped out.
Why: GHL's stage order is not a sales path. Treating it as a straight line would show
nonsense like deals "moving" from Closed to Cancelled and give wrong conversion rates.

## 12. Dates
Found: the whole campaign was imported on one day (2026-09-04).
Decision: Don't filter or trend by date; only use dates to rule out records outside
the agency's batch.
Why: The import date is not when leads really arrived during the 3 months, so a
"leads per week" chart would be meaningless.


1. Why not just filter by the Sales Pipeline?
Because a pipeline holds deals, not leads. About 117 of the agency’s leads never became a deal, so filtering by pipeline would drop them. Every source would then look like it converts almost 100%, which is survivorship bias. The Sales Pipeline also contains 33 deals from the sandbox demo data. So I decide scope by the lead (the agency tag) and only then keep that lead’s deals in the Sales Pipeline.

2. Why keep the original duplicate instead of the copy?
The original is the earliest record, the moment the person first came in. Its source is the channel that actually brought them. The copy was created about a minute later with a .2 email and usually a different source, so keeping it would credit the wrong channel. This is called first-touch attribution. Removing the copy also stops one person counting as two leads in two different channels.

3. Why keep the $145,000 deals as wins instead of deleting them?
Two separate facts are recorded: did the sale happen? and how much was it worth? The deal is in Closed and marked won, so the sale happened. Only the amount is clearly wrong (17× a typical sale). Deleting the deal would lower that source’s win rate, which is wrong. Counting the amount would inflate revenue 2.5×. So the deal counts as a win, and only its value is left out of revenue.

4. Why does “No Show” count as reaching “Booked a call”?
You can only fail to show up to a call you booked. So anyone in No Show definitely got as far as booking, and stopped there. Counting them at the booking step means the funnel shows correctly that they booked but never had the call. The same logic applies to Cancelled (booked, then cancelled), Disqualified (opted in, then ruled out) and Lost (had the call, then said no).

All four answers share one idea: every rule exists to make one source fairly comparable with another. If you remember that, you can work out any of the other decisions on the spot.