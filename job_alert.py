#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
job_alert.py — OpenClaw Job Hunt Sender
Runs jobspy scraping, deduplicates, sends new jobs to Telegram Bot API directly.
No LLM tool calls needed. Python handles everything.

Usage: python job_alert.py [--hours 24] [--profiles J N R G]
Profiles: J (Supply Chain/Data), N (Admin/Social), R (IT Analyst), G (General Admin)
"""

import os
import json, subprocess, argparse, urllib.request, urllib.error, sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent
TRACKER_FILE = WORKSPACE / "job-tracker-seen-jobs.md"
SCRAPER      = WORKSPACE / "run_jobspy_24h.py"
BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID      = os.environ.get("TELEGRAM_CHAT_ID", "747174717")
MAX_PER_PROFILE = 25   # max jobs sent per profile per run


def parse_ids(raw):
    """Split a comma-separated chat-ID string into a clean list of IDs.

    Lets any recipient env var hold multiple accounts, e.g.
    TELEGRAM_CHAT_ID_BROADCAST="111,222,333".
    """
    return [c.strip() for c in (raw or "").split(",") if c.strip()]


# Broadcast recipients — receive ALL jobs from ALL profiles (e.g. shared viewers).
# Comma-separate to add as many accounts as you like.
BROADCAST_CHAT_IDS = parse_ids(os.environ.get("TELEGRAM_CHAT_ID_BROADCAST"))

# Per-profile Telegram recipients (each may be a comma-separated list of chat IDs;
# falls back to the default CHAT_ID when a profile's var is not set).
CHAT_IDS = {
    "J": parse_ids(os.environ.get("TELEGRAM_CHAT_ID_J")) or [CHAT_ID],
    "N": parse_ids(os.environ.get("TELEGRAM_CHAT_ID_N")) or [CHAT_ID],
    "R": parse_ids(os.environ.get("TELEGRAM_CHAT_ID_R")) or [CHAT_ID],
    "G": parse_ids(os.environ.get("TELEGRAM_CHAT_ID_G")) or [CHAT_ID],
}

# Salary estimates for Calgary market when employer doesn't post salary
SALARY_ESTIMATES = [
    # Supply Chain / Procurement / Logistics
    ("supply chain manager",      (90000, 120000)),
    ("procurement manager",       (90000, 120000)),
    ("logistics manager",         (85000, 115000)),
    ("materials manager",         (85000, 115000)),
    ("category manager",          (90000, 120000)),
    ("sourcing manager",          (88000, 118000)),
    ("contract manager",          (88000, 115000)),
    ("vendor manager",            (85000, 110000)),
    ("transportation manager",    (85000, 110000)),
    ("inventory manager",         (80000, 105000)),
    ("supply chain analyst",      (75000, 95000)),
    ("supply chain coordinator",  (65000, 82000)),
    ("supply chain specialist",   (70000, 90000)),
    ("supply chain planner",      (72000, 92000)),
    ("procurement analyst",       (75000, 95000)),
    ("procurement coordinator",   (65000, 82000)),
    ("procurement specialist",    (72000, 90000)),
    ("purchasing coordinator",    (62000, 80000)),
    ("purchasing agent",          (60000, 78000)),
    ("buyer",                     (68000, 90000)),
    ("sourcing analyst",          (72000, 92000)),
    ("sourcing specialist",       (70000, 88000)),
    ("category analyst",          (72000, 92000)),
    ("contract analyst",          (68000, 88000)),
    ("contracts administrator",   (65000, 85000)),
    ("logistics analyst",         (65000, 85000)),
    ("logistics coordinator",     (60000, 78000)),
    ("inventory analyst",         (65000, 82000)),
    ("inventory coordinator",     (58000, 75000)),
    ("demand planner",            (72000, 92000)),
    ("materials planner",         (68000, 88000)),
    ("transportation analyst",    (68000, 88000)),
    ("freight coordinator",       (58000, 75000)),
    ("distribution coordinator",  (60000, 78000)),
    ("import export",             (60000, 80000)),
    ("forecasting analyst",       (72000, 92000)),
    ("operations analyst",        (68000, 88000)),
    ("operations coordinator",    (60000, 78000)),
    ("process improvement",       (70000, 90000)),
    # Data / BI / IT Analyst
    ("business analyst",          (75000, 95000)),
    ("data analyst",              (70000, 90000)),
    ("bi analyst",                (75000, 95000)),
    ("business intelligence",     (75000, 95000)),
    ("reporting analyst",         (65000, 85000)),
    ("systems analyst",           (70000, 90000)),
    ("power bi",                  (72000, 92000)),
    ("it support",                (52000, 68000)),
    ("help desk",                 (48000, 65000)),
    ("service desk",              (48000, 65000)),
    ("desktop support",           (50000, 67000)),
    ("application support",       (58000, 75000)),
    ("sharepoint",                (65000, 82000)),
    ("it coordinator",            (58000, 75000)),
    # Coordinator / Social Services / HR
    ("program coordinator",       (60000, 78000)),
    ("project coordinator",       (62000, 82000)),
    ("hr coordinator",            (58000, 75000)),
    ("hr specialist",             (62000, 82000)),
    ("case manager",              (62000, 80000)),
    ("social worker",             (60000, 80000)),
    ("settlement coordinator",    (58000, 75000)),
    ("intake coordinator",        (58000, 74000)),
    ("client advisor",            (58000, 76000)),
    ("student advisor",           (58000, 75000)),
    ("employment advisor",        (58000, 76000)),
    ("policy analyst",            (68000, 88000)),
    ("research coordinator",      (60000, 78000)),
    ("training coordinator",      (58000, 75000)),
    ("wellness coordinator",      (56000, 72000)),
    ("benefits coordinator",      (58000, 76000)),
    ("communications coordinator",(60000, 78000)),
    # Admin / Office
    ("administrative coordinator",(52000, 68000)),
    ("office coordinator",        (50000, 65000)),
    ("administrative assistant",  (45000, 65000)),
    ("office administrator",      (48000, 65000)),
    ("receptionist",              (42000, 60000)),
    ("data entry",                (38000, 50000)),
    ("customer service",          (42000, 60000)),
    ("billing coordinator",       (52000, 67000)),
    ("accounts coordinator",      (52000, 68000)),
    ("scheduling coordinator",    (50000, 65000)),
    ("facilities coordinator",    (55000, 72000)),
    ("event coordinator",         (52000, 68000)),
    ("marketing coordinator",     (52000, 70000)),
    ("document controller",       (55000, 72000)),
    ("property administrator",    (52000, 68000)),
    # Fallback by seniority keyword
    ("coordinator",               (55000, 72000)),
    ("specialist",                (62000, 82000)),
    ("analyst",                   (65000, 85000)),
    ("advisor",                   (60000, 78000)),
    ("assistant",                 (44000, 58000)),
    ("administrator",             (50000, 65000)),
]


def parse_min_years(description):
    """Extract the minimum years of experience required from a job description."""
    if not description:
        return None
    import re
    desc = str(description).lower()
    m = re.search(r'(\d+)\s*[-–to]+\s*(\d+)\s*\+?\s*years?', desc)
    if m:
        return int(m.group(2))
    m = re.search(r'(?:minimum|at least|min\.?)\s+(\d+)\s*\+?\s*years?', desc)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*\+\s*years?', desc)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*years?\s+(?:of\s+)?(?:experience|exp)', desc)
    if m:
        return int(m.group(1))
    return None


def estimate_salary(title):
    """Return market estimate salary string for Calgary based on job title."""
    t = title.lower()
    for keyword, (low, high) in SALARY_ESTIMATES:
        if keyword in t:
            return f"~${low//1000}K–${high//1000}K CAD (market estimate, Calgary)"
    return "Salary not listed"


def salary_upper_estimate(title):
    """Return upper salary estimate value, or None if not found."""
    t = title.lower()
    for keyword, (low, high) in SALARY_ESTIMATES:
        if keyword in t:
            return high
    return None


# Manager titles exempt from the global "manager" exclusion
APPROVED_MANAGER_TITLES = [
    "supply chain manager", "procurement manager", "logistics manager",
    "category manager", "sourcing manager", "contract manager",
    "materials manager", "inventory manager", "transportation manager",
    "vendor manager", "purchasing manager", "case manager",
    "program manager",
]

# Non-Alberta province codes and cities — rejected even if is_remote=True
NON_AB_PROVINCES = [", on", ", bc", ", mb", ", sk", ", qc", ", ns", ", nb", ", nl", ", pe", ", nt", ", yt", ", nu"]
NON_AB_CITIES    = ["toronto", "vancouver", "montreal", "ottawa", "winnipeg",
                    "halifax", "victoria", "saskatoon", "regina"]

# Max years of experience per profile (from job description)
EXPERIENCE_MAX = {"J": 5, "R": 5, "N": 10, "G": 10}

# Global title exclusions applied to every profile
GLOBAL_EXCLUDE = [
    # Licensed / regulated healthcare
    "lpn", "licensed practical", "registered nurse", " rn ", " rn,",
    "health care aide", " hca ", "personal support worker", " psw ",
    "physician", " md ", "surgeon", "dentist", "dental hygienist",
    "optometrist", "chiropractor", "physiotherapist", "occupational therapist",
    "speech language", "speech therapist", "radiologist", "paramedic",
    " emt ", "pharmacy technician", "medical laboratory", "lab technician",
    "diagnostic imaging", "respiratory therapist",
    # Nursing / medical / health care (broader)
    "nursing", "nurse", "dental", "medical ", "health care", "healthcare aide",
    # Retail / food / hospitality
    "food service", "food and beverage", " f&b ", "restaurant",
    "kitchen", " chef ", "bartender", "barista", "cashier",
    "grocery", "retail sales", "retail associate", "store associate",
    "fashion ", "apparel", "clothing store", "loss prevention",
    "retail ",
    # Trades / physical labour
    "electrician", "plumber", "hvac", "welder", "carpenter",
    "landscap", "janitorial", "custodian",
    "mechanic", "mechanical engineer", "maintenance worker",
    # Driving
    "truck driver", "bus driver", " cdl ", "delivery driver",
    # Security
    "security guard",
    # Tech roles unwanted across all profiles
    "software developer", "software engineer", "devops", "full stack", "fullstack",
    # Other excluded categories
    "bilingual", "esthetician", "beauty therapist", "aesthetician",
    "seasonal ", "temporary position", "general labour", "general labor",
    "general staff", " clerk", "dispatch",
    # Intern roles
    " intern ", "internship", "co-op student", "coop student",
]


PROFILE_CONFIG = {
    "J": {
        "min_salary": 80000,
        "exclude": ["director", "vp", "vice president", "sr.", " sr ",
                    "warehouse", "stocker", "receiver", "shipper", "handler",
                    "labou", "driver", "forklift", "intern",
                    "c-suite", "chief", "president"],
    },
    "N": {
        "min_salary": 65000,
        "exclude": ["director", "vp", "vice president", "executive",
                    "engineer", "developer", "physician", "registered nurse",
                    " rpn ", "warehouse", "stocker",
                    "software", "devops", "infrastructure", "machine learning",
                    "data engineer", "backend", "frontend",
                    "cybersecurity", "network engineer",
                    "dynamics 365", "microsoft dynamics", "erp", "sap ",
                    "project manager", "it project"],
    },
    "R": {
        "min_salary": 55000,
        "exclude": ["senior", "lead", "manager", "supervisor", "director",
                    "principal", "architect", "sr.", " sr ",
                    "customer service", "customer support",
                    "sales", "merchandising", "forklift", "driver"],
    },
    "G": {
        "min_salary": 45000,
        "exclude": ["senior", "director", "manager", "executive",
                    "chief", "deputy", "supply chain", "procurement",
                    "logistics", "contract specialist"],
    },
}


def tg_send(text, chat_id=None):
    """Send a plain-text message to Telegram. Auto-trims to 4000 chars."""
    if chat_id is None:
        chat_id = CHAT_ID
    if len(text) > 4000:
        text = text[:3990] + "..."
    payload = json.dumps({
        "chat_id": str(chat_id),
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
    except urllib.error.HTTPError as e:
        # Telegram puts the real reason in the JSON body, e.g.
        # "Bad Request: chat not found" or
        # "Forbidden: bot is not a member of the group chat".
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        print(f"  [TG ERROR] chat_id={chat_id} HTTP {e.code}: {body or e.reason}")
        return False
    except Exception as e:
        print(f"  [TG ERROR] chat_id={chat_id} {e}")
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
    title   = job.get("title", "")
    if not min_amt or min_amt <= 0:
        return estimate_salary(title)
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
    raw_date = str(job.get("date_posted") or "")[:10]
    date     = raw_date if raw_date and raw_date != "None" else datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
    chat_ids = CHAT_IDS.get(profile, [CHAT_ID])

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

        # Title exclude filter — profile-specific + global
        title_lower = (job.get("title") or "").lower()
        if any(ex in title_lower for ex in cfg["exclude"]):
            continue
        if any(ex in title_lower for ex in GLOBAL_EXCLUDE):
            continue

        # Manager filter: block "manager" titles unless it's an approved SCM/case manager
        if "manager" in title_lower:
            if not any(approved in title_lower for approved in APPROVED_MANAGER_TITLES):
                continue

        # Upper salary estimate filter: skip jobs where best-case estimate < $60K
        upper = salary_upper_estimate(job.get("title", ""))
        if upper is not None and upper < 60000:
            continue

        # Location filter: reject known non-AB province codes and cities
        loc = (job.get("location") or "").lower()
        is_remote = bool(job.get("is_remote"))
        if any(p in loc for p in NON_AB_PROVINCES) or any(c in loc for c in NON_AB_CITIES):
            continue
        if not is_remote and not any(k in loc for k in ("calgary", "alberta", ", ab", "ab,", "ab ")):
            continue

        # Experience filter
        max_exp = EXPERIENCE_MAX.get(profile)
        if max_exp:
            min_years = parse_min_years(job.get("description") or "")
            if min_years is not None and min_years > max_exp:
                continue

        # Salary floor (only reject if salary explicitly listed below minimum)
        ann = annual_salary(job)
        if ann and ann < cfg["min_salary"]:
            continue

        # Send to every recipient configured for this profile
        msg = format_job_message(job, profile)
        title_disp = job.get("title", "")
        co_disp    = job.get("company", "")
        print(f"  -> {title_disp} @ {co_disp}")

        delivered = False
        for cid in chat_ids:
            if tg_send(msg, chat_id=cid):
                delivered = True

        if delivered:
            seen_urls.add(url)
            append_tracker(title_disp, co_disp, profile, url)
            sent += 1
            # Also send to broadcast recipients (all-profiles viewers) if configured,
            # skipping anyone who already got it as a profile recipient
            for bcast_id in BROADCAST_CHAT_IDS:
                if bcast_id not in chat_ids:
                    tg_send(msg, chat_id=bcast_id)
        else:
            print(f"     [WARN] Telegram send failed to all recipients, skipping")

    print(f"  [{profile}] Sent {sent} new jobs")
    return sent


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Job Alert Sender")
    parser.add_argument("--hours",    type=int, default=24,
                        help="Hours old filter (default: 24, max: 48)")
    parser.add_argument("--profiles", nargs="+",
                        default=["J", "N", "R", "G"],
                        help="Profiles to process (J, N, R, G)")
    args = parser.parse_args()

    hours    = min(args.hours, 48)
    profiles = [p.upper() for p in args.profiles if p.upper() in PROFILE_CONFIG]

    print(f"\n{'='*60}")
    print(f"JOB ALERT — {datetime.now().strftime('%Y-%m-%d %H:%M')} MST")
    print(f"Profiles: {profiles} | Freshness: last {hours}h")
    print(f"{'='*60}")

    # Show exactly which recipients are configured, so a missing/misnamed
    # secret (e.g. an empty broadcast list) is obvious in the logs.
    bcast_disp = ", ".join(BROADCAST_CHAT_IDS) if BROADCAST_CHAT_IDS else "none"
    prof_disp  = ", ".join(f"{p}:{len(CHAT_IDS[p])}" for p in ["J", "N", "R", "G"])
    print(f"Recipients — default: {CHAT_ID} | broadcast: {bcast_disp} | per-profile counts: {prof_disp}")
    if not BROADCAST_CHAT_IDS:
        print("  [NOTE] No broadcast recipients — set TELEGRAM_CHAT_ID_BROADCAST to a group/chat ID to fan out all jobs.")

    seen_urls = load_seen_urls()
    print(f"Tracker: {len(seen_urls)} URLs already seen")

    # Announce the run start so recipients get an immediate confirmation the
    # moment a hunt kicks off — for every run type: scheduled auto-run or a
    # manual "Run workflow" dispatch.
    start_msg = (
        f"🚀 Got it — job hunt started ({datetime.now().strftime('%Y-%m-%d %H:%M')} MST)\n"
        f"Scanning: {', '.join(profiles)}\n"
        f"⏳ Give me ~30 minutes — new jobs will land here as they come in."
    )
    tg_send(start_msg)
    for bcast_id in BROADCAST_CHAT_IDS:
        if bcast_id != CHAT_ID:
            tg_send(start_msg, chat_id=bcast_id)

    summary = {}
    for profile in profiles:
        count = process_profile(profile, hours, seen_urls)
        summary[profile] = count

    total = sum(summary.values())

    # Send summary to default chat
    lines = "\n".join(f"• {p}: {c} jobs" for p, c in summary.items())
    summary_msg = (
        f"✅ Job Hunt Done — {datetime.now().strftime('%Y-%m-%d %H:%M')} MST\n"
        f"{lines}\n"
        f"Total: {total} new leads | Sources: jobspy + talentegg + eluta"
    )
    print(f"\n{summary_msg}")
    tg_send(summary_msg)
    # Send the same summary to any broadcast recipients (e.g. a shared group).
    # This runs every completed hunt, so the group always gets at least the
    # summary — a clear, visible confirmation the chat ID is wired correctly.
    for bcast_id in BROADCAST_CHAT_IDS:
        if bcast_id != CHAT_ID:
            ok = tg_send(summary_msg, chat_id=bcast_id)
            print(f"  [broadcast summary] {bcast_id}: {'sent' if ok else 'FAILED — see [TG ERROR] above'}")

    print(f"{'='*60}\nDONE")


if __name__ == "__main__":
    main()
