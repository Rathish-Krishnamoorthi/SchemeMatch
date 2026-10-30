"""
Enrich schemes in MongoDB with rule-based eligibility dicts inferred from
scheme names, descriptions, and known government scheme requirements.

Run: python enrich_eligibility.py

This script adds eligibility rules only where they can be reliably inferred.
Schemes where rules cannot be reliably inferred are left with empty dicts
(they remain NEEDS_VERIFICATION — that is intentional and honest).
"""
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parent / ".env")

uri = os.getenv("MONGODB_URI")
db_name = os.getenv("DATABASE_NAME", "schemematch")

# ─── Rule inference patterns ─────────────────────────────────────────────────
# Each entry: (match_fn, partial_eligibility_dict)
# match_fn receives the full scheme document.
# Partial dicts are MERGED — a scheme can match multiple patterns.

def name_desc(s: dict) -> str:
    return (s.get("name", "") + " " + s.get("description", "") + " " + s.get("benefits", "")).lower()


# ── Category (social) rules ───────────────────────────────────────────────────
SC_KEYWORDS = [
    "scheduled caste", r"\bsc\b", "dalit", "ambedkar", "sc student",
    "sc/st", "sc st", "ramai", "eklavya hostel", "post-matric scholarship for sc",
    "national fellowship for sc", "pre-matric scholarship for sc", "nsp-pre-matric-sc",
    "sc-hostels", "sc-housing", "sc-st-hub", "sc-st-coaching",
]
ST_KEYWORDS = [
    "scheduled tribe", r"\bst\b", "tribal", "adivasi", "van dhan",
    "eklavya model", "emrs", "trifed", "tribal sub-plan", "tribes india",
    "national fellowship for st", "post-matric scholarship for st",
    "eklavya-fellowship",
]
OBC_KEYWORDS = [
    "other backward class", r"\bobc\b", "obc student", "post-matric scholarship for obc",
    "national fellowship for obc",
]
SC_OR_ST_KEYWORDS = ["sc/st", "sc st hub", "sca to scsp"]
MINORITY_KEYWORDS = [
    "minority", "madrasa", "waqf", "wakf", "nmdfc", "maulana azad",
    "begum hazrat", "nai manzil", "himayat", "merit-cum-means minority",
    "post-matric minority", "pre-matric minority",
]
EWS_KEYWORDS = [r"\bews\b", "economically weaker section"]

# ── Occupation rules ──────────────────────────────────────────────────────────
FARMER_ONLY = [
    "pm-kisan", "pmfby", "pkvy", "kcc", "pm-aasha", "enam",
    "kalia-odisha", "rythu-bandhu", "fasal-rin", "pm-pmsry",
    "nfdb-aquaculture", "pmmsy", "gramin-bhandaran", "per-drop-more-crop",
    "sugar-cane-dev", "beekeeping-mission", "dairy-entrepreneurship",
    "mgnregs-farm", "coop-dairy", "nmoop", "nmaip", "soil-health-card",
    "horticulture-cluster", "atma", "nmaet",
]
STUDENT_ONLY = [
    "pm-usp-cs", "nmms", "ntse", "kvpy", "inspire-scholarship", "csss",
    "pragati", "saksham-aicte", "ishan-uday", "jammu-kashmir-pmsss",
    "post-matric-sc", "post-matric-obc", "post-matric-st",
    "post-matric-minority", "pre-matric-minority", "pre-matric-sc",
    "merit-cum-means-minority", "begum-hazrat", "cbse-merit-scholarship",
    "scert-state-merit", "sports-scholarship-sai", "education-minority-nmdfc",
    "bpl-medical-scholarship", "pm-vidya-lakshmi", "swayam-mooc",
    "pm-yasasvi", "national-scholarship-portal", "iit-sc-st-fee-waiver",
]
FARMER_RELATED = [
    "farmer", "kisan", "agriculture", "crop", "farm", "agri",
    "horticulture", "fisheries", "livestock", "dairy", "beekeeping",
]
STUDENT_RELATED = [
    "scholarship", "student", "college", "university", "education",
    "fellowship", "coaching", "hostel for sc", "hostel for st",
    "eklavya model", "emrs",
]

# ── Age rules ─────────────────────────────────────────────────────────────────
SENIOR_KEYWORDS = ["old-age pension", "senior citizen", "pm-kmy", "pm-pmsry", "vayoshreshtha"]
YOUTH_KEYWORDS = ["youth", "young", "age 18-35", "age 15-35", "ddu-gky", "himayat", "nai manzil"]

# ── Gender rules ──────────────────────────────────────────────────────────────
WOMEN_ONLY = [
    "women", "woman", "girl", "female", "mahila", "swarnima",
    "working women hostel", "pragati", "begum hazrat", "nijashree",
    "life mission", "nulm sel woman", "stand-up india",  # stand-up india has women component
]

# ── Disability ────────────────────────────────────────────────────────────────
DISABILITY_ONLY = ["saksham", "disability", "divyang", "pwd", "differently-abled"]

# ─── Build eligibility rules for a scheme ────────────────────────────────────

def infer_eligibility(s: dict) -> dict:
    sid = s.get("scheme_id", "")
    nd = name_desc(s)
    rules: dict = {}

    # ── Social category ───────────────────────────────────────────────────────

    # SC only
    sc_match = any(re.search(p, nd) for p in SC_KEYWORDS) or sid in [
        "post-matric-sc", "pre-matric-sc", "nsp-pre-matric-sc",
        "national-fellowship-sc", "sc-housing", "sc-hostels",
        "sc-st-coaching", "sc-st-hub", "mh-gharkul", "sca-tribal-agri",
    ]
    # ST only
    st_match = any(re.search(p, nd) for p in ST_KEYWORDS) or sid in [
        "post-matric-st", "national-fellowship-st", "eklavya-fellowship",
        "eklavya-hostel", "tribal-housing", "sca-tribal-agri",
        "tribal-enterprise", "nsp-eklavya-st",
    ]
    # SC or ST
    sc_st_match = any(re.search(p, nd) for p in SC_OR_ST_KEYWORDS) or sid in [
        "sc-st-hub", "sc-st-coaching", "stand-up-india",
    ]
    # OBC only
    obc_match = any(re.search(p, nd) for p in OBC_KEYWORDS) or sid in [
        "post-matric-obc", "national-fellowship-obc",
    ]
    # Minority only
    minority_match = any(re.search(p, nd) for p in MINORITY_KEYWORDS) or sid in [
        "pre-matric-minority", "post-matric-minority",
        "merit-cum-means-minority", "maef-scholarship",
        "education-minority-nmdfc", "minority-housing",
        "minority-wakf-housing", "free-coaching-minority",
        "nai-manzil", "himayat-jk", "swarnima",
    ]

    if sc_match and not st_match and not sc_st_match:
        rules["categories"] = ["SC"]
    elif st_match and not sc_match and not sc_st_match:
        rules["categories"] = ["ST"]
    elif sc_st_match or (sc_match and st_match):
        rules["categories"] = ["SC", "ST"]
    elif obc_match:
        rules["categories"] = ["OBC"]
    elif minority_match:
        rules["categories"] = ["Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Parsi", "Zoroastrian"]

    # ── Occupation / farmer_status ─────────────────────────────────────────────
    is_farmer_scheme = (
        sid in FARMER_ONLY
        or any(k in nd for k in FARMER_RELATED)
    )
    is_student_scheme = (
        sid in STUDENT_ONLY
        or "scholarship" in nd
        or ("student" in nd and "college" in nd)
    )

    if is_farmer_scheme and not is_student_scheme:
        rules["farmer_status"] = True

    if is_student_scheme and not is_farmer_scheme:
        rules["student_status"] = True
        if "categories" not in rules:
            # Most general education schemes are open to all categories
            pass

    # ── Gender ─────────────────────────────────────────────────────────────────
    women_match = (
        any(re.search(r'\b' + k + r'\b', nd) for k in WOMEN_ONLY)
        and not re.search(r'man|men\b', nd)
    )
    if women_match or sid in [
        "pragati", "swarnima", "begum-hazrat", "working-women-hostel",
        "girl-child-scholarship-wcd",
    ]:
        rules["genders"] = ["Female"]

    # ── Age ───────────────────────────────────────────────────────────────────
    if any(re.search(p, nd) for p in SENIOR_KEYWORDS) or sid in ["pm-pmsry"]:
        rules["min_age"] = 60

    # KCC has a min age
    if sid == "kcc":
        rules["min_age"] = 18

    # Pension schemes
    if "pension" in nd and "farmer" in nd:
        rules["min_age"] = 18
        rules["max_age"] = 40  # PM-KMY: enrolment window
        rules["farmer_status"] = True

    # ── Income caps for major welfare/housing schemes ─────────────────────────
    if sid in ["pmay-gramin", "pmay-urban", "pmay-credit-link"]:
        rules["max_income"] = 1800000  # ₹18 lakh (MIG-II ceiling)

    if sid in [
        "pmay-gramin", "iay", "biju-awas", "sc-housing",
        "tribal-housing", "mh-gharkul", "jharkhand-abua-awas",
    ]:
        rules["max_income"] = 300000  # ₹3 lakh for rural poor

    # ── Disability ────────────────────────────────────────────────────────────
    if any(k in nd for k in DISABILITY_ONLY) or sid == "saksham-aicte":
        rules["disability_status"] = True

    return rules


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print(f"Connecting to {db_name}.schemes …")
    with MongoClient(uri, serverSelectionTimeoutMS=10000) as client:
        client.admin.command("ping")
        col = client[db_name]["schemes"]
        schemes = list(col.find({}))
        print(f"Found {len(schemes)} schemes.")

        enriched = updated = skipped = 0
        for s in schemes:
            rules = infer_eligibility(s)
            if not rules:
                skipped += 1
                continue
            col.update_one(
                {"_id": s["_id"]},
                {"$set": {"eligibility": rules}},
            )
            updated += 1
            enriched += len(rules)

        total_with_rules = col.count_documents({"eligibility": {"$ne": {}}})
        total_empty = col.count_documents({"eligibility": {}})
        print(f"Updated {updated} schemes with {enriched} rule entries.")
        print(f"Schemes with rules: {total_with_rules} | Still empty: {total_empty}")

        # Print summary breakdown
        print("\nBreakdown of rules applied:")
        for key in ["categories", "farmer_status", "student_status", "genders", "disability_status", "min_age", "max_income"]:
            count = col.count_documents({f"eligibility.{key}": {"$exists": True}})
            if count > 0:
                print(f"  {key}: {count} schemes")


if __name__ == "__main__":
    main()
