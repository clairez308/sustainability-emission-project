"""
Loads the cleaned NPRI pollution-prevention data into MongoDB as one
document per facility-year.

Design note: the original scaffold assumed NPRI published an itemized,
variable-length list of P2 activities per facility (material
substitution, equipment modification, etc. -- see the README's original
"why Mongo" pitch). Once fetch_npri.js pulled the real bulk data, that
turned out not to exist as a public dataset: pollution-waste.canada.ca's
facility search API only exposes two booleans per facility-year
(hasP2Plan, hasP2Activity) -- there is no itemized category list to nest.
So this loader (and data_prep/config.py's NPRI_P2_COLUMNS) were scaled
down to match: each Mongo document is a flat facility-year record with
those two flags, not a nested activities array. Still a legitimate
document-store choice (schema-light, no join needed against GHGRP data
until reconciliation), just a smaller one than originally scoped -- and
it's all the headline finding (% of top emitters with no P2 plan)
actually needs.

Setup:
    pip install pymongo pandas
    Free option: MongoDB Atlas M0 cluster.

Before running:
    Run data_prep/clean_and_prepare.py first — expects
    data/clean/npri_p2_activities.csv to exist.

Run:
    export MONGO_URI="mongodb+srv://<user>:<password>@<cluster>.mongodb.net"
    python load_to_mongo.py
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CLEAN_DIR = Path(__file__).resolve().parent.parent / "data" / "clean"
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "emissions_analytics"
COLLECTION_NAME = "facility_p2_activities"


def main():
    path = CLEAN_DIR / "npri_p2_activities.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run data_prep/clean_and_prepare.py first")

    df = pd.read_csv(path)

    client = MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]
    collection.delete_many({})

    documents = []
    for row in df.itertuples(index=False):
        documents.append(
            {
                "facility_id": None if pd.isna(row.facility_id) else int(row.facility_id),
                "npri_id": None if pd.isna(row.npri_id) else int(row.npri_id),
                "year": None if pd.isna(row.year) else int(row.year),
                "has_p2_plan": bool(row.has_p2_plan),
                "has_p2_activity": bool(row.has_p2_activity),
            }
        )

    if documents:
        result = collection.insert_many(documents)
        print(f"inserted {len(result.inserted_ids)} facility-year P2 documents")

    collection.create_index("facility_id")
    collection.create_index([("facility_id", 1), ("year", 1)])
    print("created indexes on facility_id, (facility_id, year)")


if __name__ == "__main__":
    main()
