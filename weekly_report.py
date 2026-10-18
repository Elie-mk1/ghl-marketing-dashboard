"""Weekly AI summary: turns the dashboard numbers into a short plain-English email for the owner.

Input : site/data.json   (counts only - no names or emails, so it is safe to send to an AI API)
Output: one email, sent every Monday morning by .github/workflows/weekly-report.yml

How it stays trustworthy:
  1. The budget decision comes from metrics.py (fixed rules). The AI explains it, it never makes it.
  2. Every number the AI writes is checked against the real numbers. One unknown number = rejected.
  3. If the AI fails twice (or there is no AI key), a plain template email is sent instead.

Run locally:  python weekly_report.py --dry-run   (prints the email instead of sending it)
"""
import json
import os
import re
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------- settings
DASHBOARD_URL = "https://elie-mk1.github.io/ghl-marketing-dashboard/"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")   # free tier; change here if Google renames it
MAX_WORDS = 160          # the owner should read it in under a minute
AI_ATTEMPTS = 2          # tries before falling back to the template
DRY_RUN = "--dry-run" in sys.argv

data = json.load(open("site/data.json"))
P, advice = data["by_source"], data["advice"]
paid = [s for s in advice["ranked"] if P[s]["group"] == "Paid ads"]


def money(n):
    return f"${n:,.0f}"


# ---------------------------------------------------------------- the facts the AI is allowed to use
def build_facts():
    return {
        "decision": [line for line in (advice["headline"], advice["subline"]) if line],
        "caution": advice["caution"],
        "paid_ad_channels_ranked": [
            {"source": s, "revenue_per_lead_usd": P[s]["revenue_per_lead"], "sales": P[s]["won"],
             "leads": P[s]["leads"], "revenue_usd": P[s]["revenue"],
             "lead_to_sale_rate_pct": round(P[s]["win_rate"] * 100)}
            for s in paid
        ],
        "other_channels": [
            {"source": s, "group": P[s]["group"], "revenue_per_lead_usd": P[s]["revenue_per_lead"],
             "sales": P[s]["won"], "leads": P[s]["leads"]}
            for s in data["sources"] if s not in paid
        ],
    }


PROMPT = """You write a short Monday-morning email for a marketing agency owner who is not technical.

Rules:
- Use ONLY numbers that appear in DATA. Do not calculate anything new (no sums, averages, differences or new percentages).
- The budget decision is already made (DATA.decision). Explain it; never change or contradict it.
- Name each source you mention. Never combine sources into one total.
- Plain text, no markdown, no bullet points, no greeting other than "Hi," and no sign-off.

Format exactly:
SUBJECT: <at most 8 words>
<body: 3 short paragraphs, at most {max_words} words in total>
Paragraph 1: the decision. Paragraph 2: why, using revenue per lead and sales for the channels named in the decision.
Paragraph 3: one thing to keep in mind, based on DATA.caution.

DATA:
{facts}
"""


# ---------------------------------------------------------------- AI call (Gemini, free tier)
def ask_gemini(prompt):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("no GEMINI_API_KEY set")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},   # key in a header, never in the URL
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Gemini returned HTTP {r.status_code}")
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts).strip()


# ---------------------------------------------------------------- guardrails
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_in(text):
    return {n.replace(",", "").rstrip(".") for n in NUMBER.findall(text)}


def check(subject, body, facts):
    """Returns a list of problems; an empty list means the email is safe to send."""
    problems = []
    allowed = numbers_in(json.dumps(facts))
    unknown = sorted(numbers_in(subject + " " + body) - allowed)
    if unknown:
        problems.append(f"numbers not in the data: {', '.join(unknown)}")
    must_name = [s for s in (advice["best"], advice.get("tied_best"), advice["worst"], advice.get("tied_worst")) if s]
    missing = [s for s in must_name if s not in body]
    if missing:
        problems.append(f"doesn't name: {', '.join(missing)}")
    words = len(body.split())
    if words > MAX_WORDS + 20:
        problems.append(f"too long ({words} words)")
    if not subject:
        problems.append("no subject line")
    return problems


def parse(text):
    lines = text.strip().splitlines()
    subject = ""
    if lines and lines[0].upper().startswith("SUBJECT:"):
        subject = lines[0].split(":", 1)[1].strip()
        lines = lines[1:]
    return subject, "\n".join(lines).strip()


# ---------------------------------------------------------------- fallback: no AI needed
def template_email():
    lines = ["Hi,", "", " ".join(l for l in (advice["headline"], advice["subline"]) if l), ""]
    for s in paid:
        p = P[s]
        lines.append(f"{s}: {money(p['revenue_per_lead'])} per lead ({p['won']} sales from {p['leads']} leads)")
    lines += ["", advice["caution"]]
    return "Your weekly marketing summary", "\n".join(lines)


# ---------------------------------------------------------------- write it
def write_email():
    facts = build_facts()
    prompt = PROMPT.format(max_words=MAX_WORDS, facts=json.dumps(facts, indent=2))
    for attempt in range(1, AI_ATTEMPTS + 1):
        try:
            subject, body = parse(ask_gemini(prompt))
        except Exception as e:          # no key, network error, quota... -> template
            print(f"AI unavailable ({e}); using the template email.")
            return (*template_email(), "template")
        problems = check(subject, body, facts)
        if not problems:
            print(f"AI draft accepted on attempt {attempt}.")
            return subject, body, "ai"
        print(f"AI draft {attempt} rejected: {'; '.join(problems)}")
    print("AI drafts kept failing the checks; using the template email.")
    return (*template_email(), "template")


def send(subject, body):
    sender = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    to = os.getenv("REPORT_TO") or sender        # course rule: while testing, only email yourself
    if not (sender and password):
        sys.exit("GMAIL_ADDRESS and GMAIL_APP_PASSWORD are needed to send (or use --dry-run).")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, sender, to
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)
    print("Email sent.")             # addresses are never printed into the logs


if __name__ == "__main__":
    subject, body, how = write_email()
    footer = (f"\n\nFull dashboard: {DASHBOARD_URL}\n\n"
              + ("Written by AI from this week's dashboard numbers; every figure was checked against the data."
                 if how == "ai" else "Generated automatically from this week's dashboard numbers."))
    subject = f"{subject} ({datetime.now(timezone.utc):%d %b})"
    body = body + footer
    if DRY_RUN:
        print(f"\n--- SUBJECT: {subject}\n{body}")
    else:
        send(subject, body)
