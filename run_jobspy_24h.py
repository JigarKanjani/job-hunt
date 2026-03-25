#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JobSpy 24h Scraper — All 4 Profiles | MULTI-SOURCE: LinkedIn > Indeed > ZipRecruiter
Outputs: jobspy_latest_[profile].json in workspace directory
Usage: python run_jobspy_24h.py [--profile JIGAR|NEELAM|XYZ|ABC|ALL] [--hours 24]
Default: runs ALL profiles, hours_old=24 (max 48)
"""

import subprocess, sys, os, json, argparse, re
from datetime import datetime

# Auto-install jobspy if needed
try:
    from jobspy import scrape_jobs
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'python-jobspy==0.37.0'], check=True)
    from jobspy import scrape_jobs

import pandas as pd

WORKSPACE = os.path.dirname(os.path.abspath(__file__))

PROFILES = {
    # ─── JIGAR ───────────────────────────────────────────────────────────────
    # Post-grad Supply Chain + Data Science (SAIT 2024). $80K+ CAD. Calgary.
    # Strategy: sweep every supply chain title variant + all analyst/BI roles.
    # Include filter ensures only desk/knowledge roles pass (no warehouse/labour).
    # Exclude senior/lead (entry-level, <2 yrs exp). Exclude Edmonton (too far).
    "JIGAR": {
        "search_terms": [
            # ── Supply Chain family ──
            "Supply Chain Analyst Calgary",
            "Supply Chain Coordinator Calgary",
            "Supply Chain Specialist Calgary",
            # ── Procurement / Purchasing ──
            "Procurement Analyst Calgary",
            "Procurement Coordinator Calgary",
            "Procurement Specialist Calgary",
            "Purchasing Coordinator Calgary",
            # ── Logistics / Inventory / Planning ──
            "Logistics Analyst Calgary",
            "Logistics Coordinator Calgary",
            "Inventory Analyst Calgary",
            "Demand Planner Calgary",
            "Materials Planner Calgary",
            # ── Operations / Process ──
            "Operations Analyst Calgary",
            "Operations Coordinator Calgary",
            "Process Improvement Analyst Calgary",
            # ── Data / BI / Reporting ──
            "Data Analyst Calgary",
            "Business Analyst Calgary",
            "BI Analyst Calgary",
            "Reporting Analyst Calgary",
            # ── Additional targeted terms ──
            "Inventory Coordinator Calgary",
            "Category Analyst Calgary",
            "Junior Analyst Calgary",
            "Contracts Administrator Calgary",
            "Material Coordinator Calgary",
            # ── Remote Canada (work from anywhere in Canada) ──
            "[REMOTE] Supply Chain Analyst",
            "[REMOTE] Data Analyst",
            "[REMOTE] Business Analyst",
            "[REMOTE] Procurement Analyst",
            "[REMOTE] Supply Chain Coordinator",
        ],
        "min_salary": 80000,
        "exclude_titles": ["senior", "lead", "director", "manager", "principal",
                           "supervisor", "vp", "vice president", "edmonton",
                           "sr.", " sr ", "warehouse", "stocker", "receiver",
                           "shipper", "handler", "operator", "associate i",
                           "technician", "worker", "labou", "labor",
                           "driver", "forklift", "dispatch"],
        # At least one of these keywords must appear in the title (desk/knowledge roles only)
        "include_titles": ["analyst", "coordinator", "specialist", "planner",
                           "advisor", "procurement", "logistics", "supply chain",
                           "data", "business", "operations", "reporting",
                           "intelligence", "purchasing", "inventory"],
        "results_wanted": 40  # GitHub Actions has no LLM timeout — can afford more
    },

    # ─── NEELAM ──────────────────────────────────────────────────────────────
    # MSW, multilingual (EN/HI/SI/GU), trauma-informed, admin background. $65K+.
    # Strategy: ALL non-technical admin/coordinator/advisor/specialist roles.
    # NOT limited to non-profit — government, healthcare, corporate admin all valid.
    # Do NOT exclude "senior" — Senior Coordinator at $65K+ is a good fit.
    # Exclude only executive titles + purely technical (engineer/developer/nurse).
    "NEELAM": {
        "search_terms": [
            # ── Coordinator family (broadest category) ──
            "Program Coordinator Calgary",
            "Administrative Coordinator Calgary",
            "HR Coordinator Calgary",
            "Operations Coordinator Calgary",
            "Project Coordinator Calgary",
            "Client Services Coordinator Calgary",
            "Intake Coordinator Calgary",
            "Office Coordinator Calgary",
            "Community Outreach Coordinator Calgary",
            "Settlement Coordinator Calgary",
            # ── Advisor family ──
            "Student Advisor Calgary",
            "Employment Advisor Calgary",
            "Settlement Advisor Calgary",
            "Client Advisor Calgary",
            # ── Case / Social Services ──
            "Case Manager Calgary",
            "Social Worker Calgary",
            "Family Support Worker Calgary",
            # ── Specialist / Analyst (non-technical) ──
            "HR Specialist Calgary",
            "Research Coordinator Calgary",
            "Policy Analyst Calgary",
            # ── Additional targeted terms ──
            "Training Coordinator Calgary",
            "Wellness Coordinator Calgary",
            "Communications Coordinator Calgary",
            "Volunteer Coordinator Calgary",
            "Benefits Coordinator Calgary",
            "Mental Health Worker Calgary",
            "Office Administrator Calgary",
            # ── Remote Canada ──
            "[REMOTE] Program Coordinator",
            "[REMOTE] HR Coordinator",
            "[REMOTE] Case Manager",
            "[REMOTE] Administrative Coordinator",
            "[REMOTE] Case Manager",
        ],
        "min_salary": 65000,
        "exclude_titles": ["director", "vp", "vice president", "executive",
                           "engineer", "developer", "physician", "pharmacist",
                           "registered nurse", "rpn", "warehouse", "stocker",
                           "shipper", "handler", "operator", "worker i",
                           "labou", "labor",
                           "software", "devops", "infrastructure", "machine learning",
                           "data engineer", "backend", "frontend", "full stack",
                           "fullstack", "cybersecurity", "network engineer",
                           "cloud engineer"],
        "include_titles": ["coordinator", "advisor", "manager", "worker",
                           "specialist", "analyst", "administrator", "counsellor",
                           "counselor", "liaison", "intake", "outreach",
                           "officer", "assistant", "facilitator",
                           "planner", "navigator"],
        "results_wanted": 40  # GitHub Actions has no LLM timeout — can afford more
    },

    # ─── XYZ ─────────────────────────────────────────────────────────────────
    # AHS IT intern 2024-2025, SharePoint/ITSM/PowerShell. $55K+. Entry-level only.
    # Strategy: EXPANDED beyond IT support — now covers full analyst spectrum.
    # Calgary has strong BA/DA market in energy, gov, healthcare, finance.
    # Hard exclude all senior/lead/manager — this is a junior-only profile.
    "XYZ": {
        "search_terms": [
            # ── Business / Data Analyst family ──
            "Business Analyst Calgary",
            "Data Analyst Calgary",
            "BI Analyst Calgary",
            "Business Intelligence Analyst Calgary",
            "Reporting Analyst Calgary",
            "Systems Analyst Calgary",
            "IT Analyst Calgary",
            "Process Analyst Calgary",
            "Power BI Analyst Calgary",
            # ── IT Support / Helpdesk ──
            "IT Support Calgary",
            "Help Desk Analyst Calgary",
            "Service Desk Analyst Calgary",
            # ── SharePoint / Power Platform ──
            "SharePoint Administrator Calgary",
            "Power Platform Developer Calgary",
            # ── Training / Coordination ──
            "Technical Trainer Calgary",
            "Learning Coordinator Calgary",
            # ── Additional targeted terms ──
            "Junior Business Analyst Calgary",
            "Junior Data Analyst Calgary",
            "Associate Analyst Calgary",
            "Application Support Analyst Calgary",
            "Desktop Support Analyst Calgary",
            "IT Coordinator Calgary",
            "Technology Coordinator Calgary",
            # ── Remote Canada ──
            "[REMOTE] Business Analyst",
            "[REMOTE] Data Analyst",
            "[REMOTE] IT Support",
            "[REMOTE] Junior Business Analyst",
            "[REMOTE] Application Support",
        ],
        "min_salary": 55000,
        "exclude_titles": ["senior", "lead", "manager", "supervisor", "director",
                           "principal", "vp", "vice president", "architect",
                           "warehouse", "stocker", "shipper", "handler",
                           "operator", "worker", "sr.", " sr ",
                           "customer service", "customer support", "retail",
                           "sales", "laborer", "labourer", "merchandising",
                           "stocking", "forklift", "driver"],
        "include_titles": ["analyst", "administrator", "trainer",
                           "coordinator", "developer", "specialist", "help desk",
                           "service desk", "helpdesk", "reporting", "intelligence",
                           "systems", "process", "automation", "platform",
                           "it support", "technical support", "application support",
                           "desktop support"],
        "results_wanted": 40  # GitHub Actions has no LLM timeout — can afford more
    },

    # ─── ABC ─────────────────────────────────────────────────────────────────
    # General admin/clerical profile. $45K+. Calgary.
    # Focused on entry/mid admin, front desk, data entry, customer service.
    "ABC": {
        "search_terms": [
            "Administrative Assistant Calgary",
            "Office Administrator Calgary",
            "Receptionist Calgary",
            "Front Desk Calgary",
            "Data Entry Calgary",
            "Administrative Coordinator Calgary",
            "Office Coordinator Calgary",
            "Customer Service Representative Calgary",
            "Office Support Calgary",
            "Clerical Assistant Calgary",
        ],
        "min_salary": 45000,
        "exclude_titles": ["senior", "director", "manager", "executive",
                           "warehouse", "stocker", "shipper", "handler",
                           "operator", "worker",
                           "chief", "deputy", "supply chain", "procurement",
                           "logistics", "contract specialist", "lead",
                           "supervisor"],
        "include_titles": ["assistant", "administrator", "coordinator",
                           "receptionist", "clerk", "clerical", "front desk",
                           "data entry", "customer service", "office",
                           "administrative"],
        "results_wanted": 40  # GitHub Actions has no LLM timeout — can afford more
    }
}

def scrape_profile(profile_name, hours_old=24):
    config = PROFILES[profile_name]
    all_jobs = []
    seen_urls = set()

    for term in config["search_terms"]:
        # [REMOTE] prefix = search Canada-wide for remote roles, strip the prefix
        is_remote_search = term.startswith("[REMOTE]")
        clean_term = term.replace("[REMOTE]", "").strip()
        location = "Canada" if is_remote_search else "Calgary, Alberta, Canada"
        label = f"{clean_term} [remote Canada]" if is_remote_search else clean_term

        try:
            print(f"  [{profile_name}] Searching: {label} (last {hours_old}h)...")
            # AGGREGATORS: LinkedIn + Indeed (primary) + ZipRecruiter (full coverage)
            # All return real scraped URLs — no API credits needed
            kwargs = dict(
                site_name=["linkedin", "indeed", "zip_recruiter"],  # glassdoor: HTTP 400 on CA locations
                search_term=clean_term,
                location=location,
                results_wanted=config["results_wanted"],
                hours_old=hours_old,
                country_indeed="Canada"
            )
            if is_remote_search:
                kwargs["is_remote"] = True
            results = scrape_jobs(**kwargs)
            if results is not None and len(results) > 0:
                print(f"    -> {len(results)} raw results")
                all_jobs.append(results)
        except Exception as e:
            print(f"    [ERR] Error: {e}")

    if not all_jobs:
        return []

    df = pd.concat(all_jobs, ignore_index=True)

    # Deduplicate by URL
    df = df.drop_duplicates(subset=["job_url"], keep="first")

    # Filter excluded titles (any of these words in title = reject)
    exclude = config["exclude_titles"]
    exclude_pattern = "|".join(re.escape(e) for e in exclude)
    df = df[~df["title"].str.lower().str.contains(exclude_pattern, na=False)]

    # Filter included titles (at least one of these words must appear = desk/knowledge roles only)
    include = config.get("include_titles")
    if include:
        include_pattern = "|".join(re.escape(i) for i in include)
        df = df[df["title"].str.lower().str.contains(include_pattern, na=False)]

    # Salary filter (only if salary is listed and below minimum)
    def salary_ok(row):
        min_amt = row.get("min_amount")
        if pd.notna(min_amt) and min_amt > 0:
            # Convert hourly to annual if needed
            if row.get("interval") == "hourly":
                min_amt = min_amt * 2080
            if min_amt < config["min_salary"]:
                return False
        return True  # Keep if no salary listed (can't rule it out)

    df = df[df.apply(salary_ok, axis=1)]

    # Add metadata
    df["profile"] = profile_name
    df["scraped_at"] = datetime.utcnow().isoformat()
    df["hours_old_filter"] = hours_old

    # Prioritize by site: LinkedIn first, then Indeed, then others
    def site_priority(site_name):
        if pd.isna(site_name):
            return 99
        site_lower = str(site_name).lower()
        if 'linkedin' in site_lower:
            return 1
        elif 'indeed' in site_lower:
            return 2
        elif 'glassdoor' in site_lower:
            return 3
        elif 'zip' in site_lower:
            return 4
        else:
            return 5

    if 'site' in df.columns:
        df['site_priority'] = df['site'].apply(site_priority)
        df = df.sort_values('site_priority').drop('site_priority', axis=1)

    # Select output fields
    keep_cols = [c for c in [
        "profile", "site", "title", "company", "location",
        "job_url", "job_url_direct", "date_posted",
        "min_amount", "max_amount", "currency", "interval",
        "is_remote", "description", "scraped_at", "hours_old_filter"
    ] if c in df.columns]

    df = df[keep_cols].head(100)  # Top 100 after filtering

    jobs = json.loads(df.to_json(orient="records", date_format="iso"))
    print(f"  [{profile_name}] [OK] {len(jobs)} jobs after filter")
    return jobs

def main():
    parser = argparse.ArgumentParser(description="JobSpy 24h scraper")
    parser.add_argument("--profile", default="ALL",
                        choices=["JIGAR", "NEELAM", "XYZ", "ABC", "ALL"],
                        help="Which profile to scrape (default: ALL)")
    parser.add_argument("--hours", type=int, default=24,
                        help="Hours old filter (default: 24, max: 48)")
    args = parser.parse_args()

    hours = min(args.hours, 48)  # Enforce max 48h
    profiles = list(PROFILES.keys()) if args.profile == "ALL" else [args.profile]

    print(f"\n{'='*60}")
    print(f"JOBSPY 24H SCRAPER — {datetime.now().strftime('%Y-%m-%d %H:%M')} MST")
    print(f"Profiles: {profiles} | Freshness: last {hours}h")
    print(f"{'='*60}")

    summary = {}
    for profile in profiles:
        jobs = scrape_profile(profile, hours_old=hours)
        output_file = os.path.join(WORKSPACE, f"jobspy_latest_{profile.lower()}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({"scraped_at": datetime.utcnow().isoformat(), "hours_old": hours,
                       "count": len(jobs), "jobs": jobs}, f, indent=2, default=str)
        summary[profile] = len(jobs)
        print(f"  -> Saved: jobspy_latest_{profile.lower()}.json ({len(jobs)} jobs)")

    print(f"\n{'='*60}")
    print("SUMMARY:")
    for p, c in summary.items():
        print(f"  {p}: {c} jobs")
    print(f"Total: {sum(summary.values())} jobs")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
