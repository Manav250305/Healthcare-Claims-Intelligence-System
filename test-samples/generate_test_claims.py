import json
import random
from datetime import datetime, timedelta

DIAGNOSES = {
    "E11.9": "Type 2 diabetes",
    "I10": "Hypertension",
    "M79.3": "Panniculitis",
    "J44.9": "COPD",
    "M54.5": "Low back pain",
}

PROCEDURES = {
    "99213": "Office visit",
    "99214": "Office visit complex",
    "71020": "Chest X-ray",
    "85025": "CBC with diff",
    "80053": "Metabolic panel",
}

PATIENTS = ["John Smith", "Mary Johnson", "Robert Davis", "Patricia Brown", "Michael Wilson"]

def generate_claim():
    return {
        "patient_name": random.choice(PATIENTS),
        "dob": f"{random.randint(1950,2000)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        "gender": random.choice(["M", "F"]),
        "member_id": f"MEM{random.randint(100000,999999)}",
        "date_of_service": (datetime.now() - timedelta(days=random.randint(1,30))).strftime("%Y-%m-%d"),
        "provider": f"Dr. Provider {random.randint(1,5)}",
        "facility": "Springfield Medical Center",
        "diagnoses": list(random.sample(DIAGNOSES.keys(), random.randint(1,2))),
        "procedures": list(random.sample(PROCEDURES.keys(), random.randint(1,2))),
        "total_charge": round(random.uniform(200, 3000), 2),
        "insurance_paid": round(random.uniform(100, 2500), 2),
    }

claims = [generate_claim() for _ in range(5)]

with open("test_claims.json", "w") as f:
    json.dump(claims, f, indent=2)

for i, claim in enumerate(claims, 1):
    print(f"Test Claim {i}:")
    print(f"  Patient: {claim['patient_name']} | DOB: {claim['dob']}")
    print(f"  Diagnoses: {', '.join(claim['diagnoses'])}")
    print(f"  Total: ${claim['total_charge']}\n")

print("✅ Saved to test_claims.json")
