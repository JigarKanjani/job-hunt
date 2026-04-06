#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JobSpy 24h Scraper — All 4 Profiles | MULTI-SOURCE: LinkedIn > Indeed > ZipRecruiter + Talentegg + Eluta
Outputs: jobspy_latest_[profile].json in workspace directory
Usage: python run_jobspy_24h.py [--profile J|N|R|G|ALL] [--hours 24]
Default: runs ALL profiles, hours_old=24 (max 48)
Profiles: J (Supply Chain/Data), N (Admin/Social), R (IT Analyst), G (General Admin)
"""

import subprocess, sys, os, json, argparse, re
from datetime import datetime

# Auto-install jobspy if needed
try:
    from jobspy import scrape_jobs
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'python-jobspy==1.1.82'], check=True)
    from jobspy import scrape_jobs

import pandas as pd

WORKSPACE = os.path.dirname(os.path.abspath(__file__))

PROFILES = {
    # ─── J ───────────────────────────────────────────────────────────────────
    # Post-grad Supply Chain + Data Science (SAIT 2024). $80K+ CAD. Calgary.
    # Strategy: sweep every supply chain title variant + all analyst/BI roles.
    "J": {
        "search_terms": [
            # ── Supply Chain (all levels) ──
            "Supply Chain Analyst Calgary",
            "Supply Chain Coordinator Calgary",
            "Supply Chain Specialist Calgary",
            "Supply Chain Planner Calgary",
            "Supply Chain Manager Calgary",
            "Supply Chain Lead Calgary",
            # ── Procurement / Purchasing / Sourcing ──
            "Procurement Analyst Calgary",
            "Procurement Coordinator Calgary",
            "Procurement Specialist Calgary",
            "Procurement Manager Calgary",
            "Purchasing Coordinator Calgary",
            "Purchasing Manager Calgary",
            "Buyer Calgary",
            "Senior Buyer Calgary",
            "Strategic Sourcing Analyst Calgary",
            "Strategic Sourcing Manager Calgary",
            "Category Analyst Calgary",
            "Category Manager Calgary",
            "Sourcing Specialist Calgary",
            "Contracts Administrator Calgary",
            "Contract Manager Calgary",
            "Vendor Manager Calgary",
            "Supplier Relations Specialist Calgary",
            # ── Logistics / Inventory / Planning ──
            "Logistics Analyst Calgary",
            "Logistics Coordinator Calgary",
            "Logistics Manager Calgary",
            "Inventory Analyst Calgary",
            "Inventory Coordinator Calgary",
            "Inventory Manager Calgary",
            "Demand Planner Calgary",
            "Supply Planner Calgary",
            "Materials Planner Calgary",
            "Materials Manager Calgary",
            "Material Coordinator Calgary",
            "Transportation Analyst Calgary",
            "Transportation Manager Calgary",
            "Freight Coordinator Calgary",
            "Distribution Coordinator Calgary",
            "Import Export Coordinator Calgary",
            # ── Operations / Process ──
            "Operations Analyst Calgary",
            "Operations Coordinator Calgary",
            "Operations Manager Calgary",
            "Process Improvement Analyst Calgary",
            "Continuous Improvement Analyst Calgary",
            "Forecasting Analyst Calgary",
            "S&OP Analyst Calgary",
            "ERP Analyst Calgary",
            # ── Oil & Gas / Energy sector specific ──
            "Supply Chain Oil Gas Calgary",
            "Procurement Oil Gas Calgary",
            "Materials Coordinator Oil Gas Calgary",
            "Field Procurement Calgary",
            "Oilfield Buyer Calgary",
            "Contract Administrator Energy Calgary",
            "Spend Analyst Calgary",
            "Vendor Management Calgary",
            # ── Mining sector ──
            "Supply Chain Mining Calgary",
            "Procurement Mining Calgary",
            "Materials Coordinator Mining Calgary",
            # ── Public sector / Government ──
            "Procurement Officer Calgary",
            "Purchasing Officer Calgary",
            "Contract Administrator Government Calgary",
            # ── Remote Canada ──
            "[REMOTE] Supply Chain Manager",
            "[REMOTE] Supply Chain Analyst",
            "[REMOTE] Procurement Manager",
            "[REMOTE] Procurement Analyst",
            "[REMOTE] Logistics Manager",
            "[REMOTE] Demand Planner",
            "[REMOTE] Inventory Analyst",
            "[REMOTE] Category Manager",
        ],
        "min_salary": 80000,
        "exclude_titles": ["director", "vp", "vice president", "principal",
                           "edmonton", "sr.", " sr ", "warehouse", "stocker",
                           "receiver", "shipper", "handler", "operator",
                           "associate i", "worker", "labou", "labor",
                           "driver", "forklift", "intern",
                           "c-suite", "chief", "president"],
        "include_titles": ["analyst", "coordinator", "specialist", "planner",
                           "manager", "lead", "advisor", "procurement",
                           "logistics", "supply chain", "operations", "purchasing",
                           "inventory", "buyer", "sourcing", "transportation",
                           "contracts", "material", "vendor", "officer", "erp"],
        "results_wanted": 50
    },

    # ─── N ───────────────────────────────────────────────────────────────────
    # MSW, multilingual (EN/HI/SI/GU), trauma-informed, admin background. $65K+.
    # Strategy: ALL non-technical admin/coordinator/advisor/specialist roles.
    "N": {
        "search_terms": [
            # ── Coordinator family ──
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
                           "cloud engineer", "dynamics 365", "microsoft dynamics",
                           "erp", "sap ", "project manager", "it project",
                           "store manager", "district manager", "general manager",
                           "operations manager", "hiring manager", "regional manager",
                           "product manager", "brand manager", "office manager",
                           "senior manager"],
        "include_titles": ["coordinator", "advisor", "manager", "worker",
                           "specialist", "analyst", "administrator", "counsellor",
                           "counselor", "liaison", "intake", "outreach",
                           "officer", "assistant", "facilitator",
                           "planner", "navigator"],
        "results_wanted": 40
    },

    # ─── R ───────────────────────────────────────────────────────────────────
    # AHS IT intern 2024-2025, SharePoint/ITSM/PowerShell. $55K+. Entry-level only.
    # Strategy: EXPANDED beyond IT support — covers full analyst spectrum.
    "R": {
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
                           "customer service", "customer support",
                           "sales", "laborer", "labourer", "merchandising",
                           "stocking", "forklift", "driver"],
        "include_titles": ["analyst", "administrator", "trainer",
                           "coordinator", "developer", "specialist", "help desk",
                           "service desk", "helpdesk", "reporting", "intelligence",
                           "systems", "process", "automation", "platform",
                           "it support", "technical support", "application support",
                           "desktop support"],
        "results_wanted": 40
    },

    # ─── G ───────────────────────────────────────────────────────────────────
    # General admin/clerical profile. $45K+. Calgary.
    # Focused on entry/mid admin, front desk, data entry, customer service.
    "G": {
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
            "Administrative Support Calgary",
            "Program Assistant Calgary",
            "Client Services Calgary",
            "Office Support Calgary",
            "Scheduling Coordinator Calgary",
            "Billing Coordinator Calgary",
            "Accounts Coordinator Calgary",
            "Facilities Coordinator Calgary",
            "Health and Safety Coordinator Calgary",
            "Event Coordinator Calgary",
            "Document Controller Calgary",
            "Property Administrator Calgary",
            "Marketing Coordinator Calgary",
            "Records Administrator Calgary",
            "Community Coordinator Calgary",
        ],
        "min_salary": 45000,
        "exclude_titles": ["senior", "director", "manager", "executive",
                           "warehouse", "stocker", "shipper", "handler",
                           "operator", "worker",
                           "chief", "deputy", "supply chain", "procurement",
                           "logistics", "contract specialist", "lead",
                           "supervisor"],
        "include_titles": ["assistant", "administrator", "coordinator",
                           "receptionist", "clerical", "front desk",
                           "data entry", "customer service", "office",
                           "administrative", "specialist", "advisor", "associate",
                           "controller", "agent", "scheduler", "facilitator"],
        "results_wanted": 40
    }
}

# ── Global exclusions applied to ALL profiles ────────────────────────────────
GLOBAL_EXCLUDE_TITLES = [
    # Licensed / regulated healthcare
    "lpn", "licensed practical", "registered nurse", " rn ", " rn,",
    "health care aide", " hca ", "personal support worker", " psw ",
    "physician", " md ", "surgeon", "dentist", "dental hygienist",
    "optometrist", "chiropractor", "physiotherapist", "occupational therapist",
    "speech language", "speech therapist", "radiologist", "paramedic",
    " emt ", "emergency medical technician", "pharmacy technician",
    "medical laboratory", "lab technician", "diagnostic imaging",
    "respiratory therapist", "recreation therapist",
    # Nursing / medical / health care (broader)
    "nursing", "nurse", "dental", "medical ", "health care", "healthcare aide",
    # Retail / food / hospitality / fashion
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
    # Tech roles unwanted globally
    "software developer", "software engineer", "devops", "full stack", "fullstack",
    # Other excluded categories
    "bilingual", "esthetician", "beauty therapist", "aesthetician",
    "seasonal ", "temporary position", "general labour", "general labor",
    "general staff", " clerk", "dispatch",
    # Intern roles
    " intern ", "internship", "co-op student", "coop student",
]
# ─────────────────────────────────────────────────────────────────────────────


def scrape_talentegg(search_term, location="Calgary, Alberta"):
    """Scrape Talentegg for entry-level Canadian jobs. Returns list of job dicts."""
    try:
        import requests
        from bs4 import BeautifulSoup
        url = "https://talentegg.ca/incubator/jobs"
        params = {"keywords": search_term, "location": location}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        # Try multiple possible selectors for job listings
        selectors = [".job-listing", ".job-result", "article.job", ".job-card",
                     ".job", "[class*='job-item']", "[class*='listing']"]
        items = []
        for sel in selectors:
            items = soup.select(sel)
            if items:
                break
        for item in items:
            title_el  = item.select_one("h2, h3, h4, .job-title, [class*='title']")
            company_el = item.select_one(".company, .employer, [class*='company']")
            link_el    = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            href = link_el.get("href", "")
            if not href.startswith("http"):
                href = "https://talentegg.ca" + href
            jobs.append({
                "title":     title_el.get_text(strip=True),
                "company":   company_el.get_text(strip=True) if company_el else "",
                "location":  location,
                "job_url":   href,
                "site":      "talentegg",
                "is_remote": False,
                "date_posted": None,
                "min_amount": None,
                "max_amount": None,
                "interval":  None,
                "description": "",
                "currency":  "CAD",
            })
        return jobs
    except Exception as e:
        print(f"  [Talentegg] Skipped: {e}")
        return []


def scrape_eluta(search_term, location="Calgary, Alberta"):
    """Scrape Eluta.ca for Canadian company career page jobs. Returns list of job dicts."""
    try:
        import requests
        from bs4 import BeautifulSoup
        # Eluta aggregates from company career pages directly
        query = f"{search_term} {location}"
        url = "https://www.eluta.ca/search"
        params = {"q": search_term, "l": location}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        # Try possible selectors
        selectors = [".result", ".job-result", ".job-listing", "article",
                     "[class*='result']", "[class*='job']"]
        items = []
        for sel in selectors:
            items = soup.select(sel)
            if len(items) > 2:
                break
        for item in items:
            title_el   = item.select_one("h2, h3, h4, .title, [class*='title']")
            company_el = item.select_one(".company, .employer, [class*='company']")
            link_el    = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            href = link_el.get("href", "")
            if not href.startswith("http"):
                href = "https://www.eluta.ca" + href
            jobs.append({
                "title":     title_el.get_text(strip=True),
                "company":   company_el.get_text(strip=True) if company_el else "",
                "location":  location,
                "job_url":   href,
                "site":      "eluta",
                "is_remote": False,
                "date_posted": None,
                "min_amount": None,
                "max_amount": None,
                "interval":  None,
                "description": "",
                "currency":  "CAD",
            })
        return jobs
    except Exception as e:
        print(f"  [Eluta] Skipped: {e}")
        return []


def scrape_custom_sites(profile_name, config, hours_old=24):
    """Scrape Talentegg and Eluta for a sample of search terms. Returns DataFrame."""
    # Use first 5 non-REMOTE search terms to avoid excessive requests
    base_terms = [t for t in config["search_terms"] if not t.startswith("[REMOTE]")][:5]
    all_jobs = []
    for term in base_terms:
        # Strip location from term for cleaner queries
        clean = re.sub(r'\s+Calgary$', '', term, flags=re.IGNORECASE).strip()
        print(f"  [{profile_name}] Talentegg: {clean}...")
        all_jobs.extend(scrape_talentegg(clean))
        print(f"  [{profile_name}] Eluta: {clean}...")
        all_jobs.extend(scrape_eluta(clean))

    if not all_jobs:
        return pd.DataFrame()

    df = pd.DataFrame(all_jobs)
    df = df.drop_duplicates(subset=["job_url"], keep="first")
    return df


def scrape_profile(profile_name, hours_old=24):
    config = PROFILES[profile_name]
    all_jobs = []

    for term in config["search_terms"]:
        is_remote_search = term.startswith("[REMOTE]")
        clean_term = term.replace("[REMOTE]", "").strip()
        location = "Canada" if is_remote_search else "Calgary, Alberta, Canada"
        label = f"{clean_term} [remote Canada]" if is_remote_search else clean_term

        try:
            print(f"  [{profile_name}] Searching: {label} (last {hours_old}h)...")
            kwargs = dict(
                site_name=["linkedin", "indeed", "zip_recruiter"],
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

    # Add Talentegg + Eluta results
    custom_df = scrape_custom_sites(profile_name, config, hours_old)
    if not custom_df.empty:
        print(f"  [{profile_name}] Custom sites: {len(custom_df)} additional jobs")
        all_jobs.append(custom_df)

    if not all_jobs:
        return []

    df = pd.concat(all_jobs, ignore_index=True)

    # Deduplicate by URL
    df = df.drop_duplicates(subset=["job_url"], keep="first")

    # Filter excluded titles — profile-specific + global
    exclude = config["exclude_titles"] + GLOBAL_EXCLUDE_TITLES
    exclude_pattern = "|".join(re.escape(e) for e in exclude)
    df = df[~df["title"].str.lower().str.contains(exclude_pattern, na=False)]

    # Filter included titles (at least one of these words must appear)
    include = config.get("include_titles")
    if include:
        include_pattern = "|".join(re.escape(i) for i in include)
        df = df[df["title"].str.lower().str.contains(include_pattern, na=False)]

    # Manager filter
    _APPROVED_MANAGERS = [
        "supply chain manager", "procurement manager", "logistics manager",
        "category manager", "sourcing manager", "contract manager",
        "materials manager", "inventory manager", "transportation manager",
        "vendor manager", "purchasing manager", "case manager",
        "program manager",
    ]
    def manager_ok(title):
        t = str(title or "").lower()
        if "manager" not in t:
            return True
        return any(approved in t for approved in _APPROVED_MANAGERS)
    df = df[df["title"].apply(manager_ok)]

    # Salary filter (only if salary is listed and below minimum)
    def salary_ok(row):
        min_amt = row.get("min_amount")
        if pd.notna(min_amt) and min_amt > 0:
            if row.get("interval") == "hourly":
                min_amt = min_amt * 2080
            if min_amt < config["min_salary"]:
                return False
        return True

    df = df[df.apply(salary_ok, axis=1)]

    # Experience filter
    _EXP_MAX = {"J": 5, "R": 5, "N": 10, "G": 10}
    _max_exp = _EXP_MAX.get(profile_name)
    if _max_exp and "description" in df.columns:
        def _parse_years(desc):
            if not desc or str(desc) in ("None", "nan", ""):
                return None
            d = str(desc).lower()
            m = re.search(r'(\d+)\s*[-–to]+\s*(\d+)\s*\+?\s*years?', d)
            if m:
                return int(m.group(2))
            m = re.search(r'(?:minimum|at least|min\.?)\s+(\d+)\s*\+?\s*years?', d)
            if m:
                return int(m.group(1))
            m = re.search(r'(\d+)\s*\+\s*years?', d)
            if m:
                return int(m.group(1))
            m = re.search(r'(\d+)\s*years?\s+(?:of\s+)?(?:experience|exp)', d)
            if m:
                return int(m.group(1))
            return None
        def exp_ok(row):
            yrs = _parse_years(row.get("description"))
            return yrs is None or yrs <= _max_exp
        df = df[df.apply(exp_ok, axis=1)]

    # Location filter
    _NON_AB_PROV  = [", on", ", bc", ", mb", ", sk", ", qc", ", ns", ", nb", ", nl",
                     ", pe", ", nt", ", yt", ", nu"]
    _NON_AB_CITIES = ["toronto", "vancouver", "montreal", "ottawa", "winnipeg",
                      "halifax", "victoria", "saskatoon", "regina"]

    def location_ok(row):
        loc = str(row.get("location") or "").lower()
        is_remote = bool(row.get("is_remote"))
        if any(p in loc for p in _NON_AB_PROV):
            return False
        if any(c in loc for c in _NON_AB_CITIES):
            return False
        if is_remote:
            return True
        return ("calgary" in loc or "alberta" in loc or
                ", ab" in loc or "ab," in loc or "ab " in loc or
                not loc.strip() or loc.strip() in ("canada", "remote", "anywhere"))

    df = df[df.apply(location_ok, axis=1)]

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
        elif 'talentegg' in site_lower:
            return 5
        elif 'eluta' in site_lower:
            return 6
        else:
            return 7

    if 'site' in df.columns:
        df['site_priority'] = df['site'].apply(site_priority)
        if 'date_posted' in df.columns:
            df['date_sort'] = pd.to_datetime(df['date_posted'], errors='coerce')
            df = df.sort_values(['date_sort', 'site_priority'],
                                ascending=[False, True])
            df = df.drop(columns=['site_priority', 'date_sort'])
        else:
            df = df.sort_values('site_priority').drop('site_priority', axis=1)

    # Select output fields
    keep_cols = [c for c in [
        "profile", "site", "title", "company", "location",
        "job_url", "job_url_direct", "date_posted",
        "min_amount", "max_amount", "currency", "interval",
        "is_remote", "description", "scraped_at", "hours_old_filter"
    ] if c in df.columns]

    df = df[keep_cols]  # No artificial cap — return all qualifying jobs

    jobs = json.loads(df.to_json(orient="records", date_format="iso"))
    print(f"  [{profile_name}] [OK] {len(jobs)} jobs after filter")
    return jobs

def main():
    parser = argparse.ArgumentParser(description="JobSpy 24h scraper")
    parser.add_argument("--profile", default="ALL",
                        choices=["J", "N", "R", "G", "ALL"],
                        help="Which profile to scrape (default: ALL)")
    parser.add_argument("--hours", type=int, default=24,
                        help="Hours old filter (default: 24, max: 48)")
    args = parser.parse_args()

    hours = min(args.hours, 48)
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
