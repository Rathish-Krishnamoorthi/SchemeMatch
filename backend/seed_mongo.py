import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parent / ".env")

SCHEMES = [
    {
        "scheme_id": "pm-kisan",
        "name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "category": "Agriculture",
        "description": "A central sector scheme providing income support to eligible small and marginal farmer families.",
        "eligibility": {},
        "benefits": "₹6,000 per year in three equal instalments directly into the farmer's bank account.",
        "documents": ["Aadhaar", "Land records", "Bank passbook"],
        "application_process": ["Register on pmkisan.gov.in or via nearest Common Service Centre."],
        "official_url": "https://pmkisan.gov.in/",
        "source": "PM-KISAN official portal",
        "last_verified": None,
        "verification_note": "Eligibility rules are intentionally not asserted in this starter catalogue. Verify on the official source.",
    },
    {
        "scheme_id": "pmay-urban",
        "name": "Pradhan Mantri Awas Yojana – Urban 2.0 (PMAY-U)",
        "category": "Housing",
        "description": "Housing scheme for eligible urban households in EWS, LIG, and MIG categories.",
        "eligibility": {},
        "benefits": "Interest subsidy on home loans; beneficiary-led construction support.",
        "documents": ["Aadhaar", "Income proof", "Bank account", "No previous pucca house certificate"],
        "application_process": ["Apply via Urban Local Body or the PMAY-Urban portal."],
        "official_url": "https://pmay-urban.gov.in/",
        "source": "PMAY-Urban official portal",
        "last_verified": None,
        "verification_note": "Eligibility rules are intentionally not asserted in this starter catalogue. Verify on the official source.",
    },
    {
        "scheme_id": "pm-vishwakarma",
        "name": "PM Vishwakarma",
        "category": "Skills & Business",
        "description": "Central government scheme supporting 18 traditional artisan and craftsperson trades.",
        "eligibility": {},
        "benefits": "Free skill training, ₹15,000 toolkit incentive, and collateral-free loans up to ₹3 lakh.",
        "documents": ["Aadhaar", "Mobile number linked to Aadhaar", "Trade practitioner proof"],
        "application_process": ["Register on pmvishwakarma.gov.in via CSC or the PM Vishwakarma portal."],
        "official_url": "https://pmvishwakarma.gov.in/",
        "source": "PM Vishwakarma official portal",
        "last_verified": None,
        "verification_note": "Eligibility rules are intentionally not asserted in this starter catalogue. Verify on the official source.",
    },
    {
        "scheme_id": "pm-mudra",
        "name": "Pradhan Mantri Mudra Yojana (PMMY)",
        "category": "Skills & Business",
        "description": "Provides credit to non-corporate, non-farm micro and small enterprises through Shishu, Kishore, and Tarun categories.",
        "eligibility": {},
        "benefits": "Collateral-free loans: Shishu (up to ₹50,000), Kishore (₹50,001–₹5 lakh), Tarun (₹5–₹10 lakh).",
        "documents": ["Aadhaar", "Business plan", "Address proof", "Bank account"],
        "application_process": ["Apply at any scheduled commercial bank, RRB, MFI, or NBFC."],
        "official_url": "https://www.mudra.org.in/",
        "source": "MUDRA official website",
        "last_verified": None,
        "verification_note": "Eligibility rules are intentionally not asserted in this starter catalogue. Verify on the official source.",
    },
    {
        "scheme_id": "pm-usp-cs",
        "name": "PM-USP Central Sector Scholarship for College & University Students",
        "category": "Education",
        "description": "Scholarship for meritorious students from low-income families pursuing higher education.",
        "eligibility": {},
        "benefits": "₹10,000/year for undergraduate; ₹20,000/year for postgraduate students.",
        "documents": ["Aadhaar", "Income certificate", "10+2 marksheet", "Bank account"],
        "application_process": ["Apply on the National Scholarship Portal during the open window."],
        "official_url": "https://scholarships.gov.in/",
        "source": "National Scholarship Portal",
        "last_verified": None,
        "verification_note": "Eligibility rules are intentionally not asserted in this starter catalogue. Verify on the official source.",
    },
]

uri = os.getenv("MONGODB_URI")
if not uri:
    raise SystemExit("MONGODB_URI not set in .env")

database_name = os.getenv("DATABASE_NAME", "schemematch")
print(f"Connecting to MongoDB ({database_name}.schemes) …")

with MongoClient(uri, serverSelectionTimeoutMS=10000) as client:
    client.admin.command("ping")
    col = client[database_name]["schemes"]
    inserted = updated = 0
    for s in SCHEMES:
        r = col.replace_one({"scheme_id": s["scheme_id"]}, s, upsert=True)
        if r.upserted_id:
            inserted += 1
        else:
            updated += 1
    total = col.count_documents({})
    print(f"Done — {inserted} inserted, {updated} updated.")
    print(f"Total schemes in collection: {total}")
    print("Use the admin panel at /admin to add more schemes.")
