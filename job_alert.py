#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
job_alert.py — OpenClaw Job Hunt Sender
Runs jobspy scraping, deduplicates, sends new jobs to Telegram Bot API directly.
No LLM tool calls needed. Python handles everything.

Usage: python job_alert.py [--hours 24] [--profiles JIGAR NEELAM XYZ ABC]
"""

import os
import json, subprocess, argparse, urllib.request, sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent
TRACKER_FILE = WORKSPACE / "job-tracker-seen-jobs.md"
SCRAPER      = WORKSPACE / "run_jobspy_24h.py"
BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "8496012269:AAGTOgNyMzHpo-pc4AwJHJczSyho3A9FGZg")
CHAT_ID      = os.environ.get("TELEGRAM_CHAT_ID", "747174717")
MAX_PER_PROFILE = 10   # max jobs sent per profile per run (avoid flooding)

PROFILE_CONFIG = {
    "JIGAR": {
        "min_salary": 80000,
        "exclude": ["senior", "lead", "director", "manager", "supervisor",
                    "vp", "vice president", "sr.", " sr ", "warehouse",
                    "stocker", "receiver", "shipper", "handler", "labou",
                    "driver", "forklift", "dispatch"],
    },
    "NEELAM": {
        "min_salary": 65000,
        "exclude": ["director", "vp", "vice president", "executive",
                    "engineer", "developer", "physician", "registered nurse",
                    " rpn ", "warehouse", "stocker",
                    "software", "devops", "infrastructure", "machine learning",
                    "data engineer", "backend", "frontend", "full stack",
                    "cybersecurity", "network engineer",
                    "dynamics 365", "microsoft dynamics", "erp", "sap ",
                    "project manager", "it project"],
    },
    "XYZ": {
        "min_salary": 55000,
        "exclude": ["senior", "lead", "manager", "supervisor", "director",
                    "principal", "architect", "sr.", " sr ",
                    "customer service", "customer support", "retail",
                    "sales", "merchandising", "forklift", "driver"],
    },
    "ABC": {
        "min_salary": 45000,
        "exclude": ["senior", "director", "manager", "executive",
                    "chief", "deputy", "supply chain", "procurement",
                    "logistics", "contract specialist"],
    },
}


def tg_send(text):
    """Send a plain-text message to Telegram. Auto-trims to 4000 chars."""
    if len(text) > 4000:
        text = text[:3990] + "..."
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"  [TG ERROR] {e}")
        return False


def load_seen_urls():
    """Return set of job URLs already sent."""
    seen = set()
    if not TRACKER_FILE.exists():
        TRACKER_FILE.write_text(
            "| Title | Company | Date | Profile | URL |\n"
            "|-------|---------|------|---------|-----|\n",
            encoding="utf-8"
        )
        return seen
    for line in TRACKER_FILE.read_text(encoding="utf-8").splitlines():
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 5 and parts[4].startswith("http"):
            seen.add(parts[4])
    return seen


def append_tracker(title, company, profile, url):
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = f"| {title[:60]} | {company[:40]} | {date} | {profile} | {url} |\n"
    with open(TRACKER_FILE, "a", encoding="utf-8") as f:
        f.write(row)


def annual_salary(job):
    amt = job.get("min_amount")
    if not amt or amt <= 0:
        return None
    if job.get("interval") == "hourly":
        amt = amt * 2080
    return amt


def format_salary(job):
    min_amt = job.get("min_amount")
    max_amt = job.get("max_amount")
    if not min_amt or min_amt <= 0:
        return "Salary not listed"
    hourly = job.get("interval") == "hourly"
    if hourly:
        min_amt, max_amt = min_amt * 2080, (max_amt * 2080 if max_amt else None)
    if max_amt and max_amt > min_amt:
        return f"${int(min_amt):,}–${int(max_amt):,} CAD (posted by employer)"
    return f"${int(min_amt):,}+ CAD (posted by employer)"


def format_job_message(job, profile):
    title    = job.get("title", "N/A")
    company  = job.get("company", "N/A")
    location = job.get("location", "N/A")
    url      = job.get("job_url", "")
    date     = str(job.get("date_posted", ""))[:10]
    remote   = job.get("is_remote", False)
    work_str = "Remote" if remote else "On-site"
    salary   = format_salary(job)
    site     = (job.get("site") or "").capitalize()

    msg = (
        f"💼 {profile} — {title}\n"
        f"🏢 {company}\n"
        f"📍 {location} | {work_str}\n"
        f"💰 {salary}\n"
        f"📅 Posted: {date} | via {site}\n"
        f"\n"
        f"🔗 {url}"
    )
    return msg[:3900]


def run_scraper(profile, hours):
    """Run run_jobspy_24h.py for one profile. Returns True on success."""
    pyenv = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    print(f"  Scraping {profile} (last {hours}h)...")
    result = subprocess.run(
        [sys.executable, str(SCRAPER), "--profile", profile, "--hours", str(hours)],
        cwd=str(WORKSPACE),
        env=pyenv,
        timeout=720  # 12 min per profile max
    )
    return result.returncode == 0


def process_profile(profile, hours, seen_urls):
    """Scrape + send + update tracker. Returns count sent."""
    cfg = PROFILE_CONFIG[profile]

    # Run scraper
    ok = run_scraper(profile, hours)
    if not ok:
        print(f"  [WARN] Scraper non-zero exit for {profile}, checking output anyway")

    # Read output file
    out_file = WORKSPACE / f"jobspy_latest_{profile.lower()}.json"
    if not out_file.exists():
        print(f"  [SKIP] {profile}: no output file")
        return 0

    try:
        data = json.loads(out_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  [ERR] Cannot read {profile} output: {e}")
        return 0

    jobs = data.get("jobs", [])
    print(f"  {len(jobs)} jobs in file for {profile}")

    sent = 0
    for job in jobs:
        if sent >= MAX_PER_PROFILE:
            break

        url = job.get("job_url", "")
        if not url:
            continue

        # Dedup
        if url in seen_urls:
            continue

        # Title exclude filter
        title_lower = (job.get("title") or "").lower()
        if any(ex in title_lower for ex in cfg["exclude"]):
            continue

        # Location filter: Calgary/Alberta on-site, OR remote (workable from Calgary)
        loc = (job.get("location") or "").lower()
        is_remote = bool(job.get("is_remote"))
        if not is_remote and not any(k in loc for k in ("calgary", "alberta", ", ab", "ab,", "ab ")):
            continue

        # Salary floor (only reject if salary explicitly listed below minimum)
        ann = annual_salary(job)
        if ann and ann < cfg["min_salary"]:
            continue

        # Send to Telegram
        msg = format_job_message(job, profile)
        title_disp = job.get("title", "")
        co_disp    = job.get("company", "")
        print(f"  -> {title_disp} @ {co_disp}")

        if tg_send(msg):
            seen_urls.add(url)
            append_tracker(title_disp, co_disp, profile, url)
            sent += 1
        else:
            print(f"     [WARN] Telegram send failed, skipping")

    print(f"  [{profile}] Sent {sent} new jobs")
    return sent


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Job Alert Sender")
    parser.add_argument("--hours",    type=int, default=24,
                        help="Hours old filter (default: 24, max: 48)")
    parser.add_argument("--profiles", nargs="+",
                        default=["JIGAR", "NEELAM", "XYZ", "ABC"],
                        help="Profiles to process")
    args = parser.parse_args()

    hours    = min(args.hours, 48)
    profiles = [p.upper() for p in args.profiles if p.upper() in PROFILE_CONFIG]

    print(f"\n{'='*60}")
    print(f"JOB ALERT — {datetime.now().strftime('%Y-%m-%d %H:%M')} MST")
    print(f"Profiles: {profiles} | Freshness: last {hours}h")
    print(f"{'='*60}")

    seen_urls = load_seen_urls()
    print(f"Tracker: {len(seen_urls)} URLs already seen")

    summary = {}
    for profile in profiles:
        count = process_profile(profile, hours, seen_urls)
        summary[profile] = count

    total = sum(summary.values())

    # Send summary to Telegram
    lines = "\n".join(f"• {p}: {c} jobs" for p, c in summary.items())
    summary_msg = (
        f"✅ Job Hunt Done — {datetime.now().strftime('%Y-%m-%d %H:%M')} MST\n"
        f"{lines}\n"
        f"Total: {total} new leads | Source: jobspy"
    )
    print(f"\n{summary_msg}")
    tg_send(summary_msg)

    print(f"{'='*60}\nDONE")


if __name__ == "__main__":
    main()
