"""
The analytical core of the project: joins facility emissions (Azure
SQL) with pollution-prevention activity (MongoDB) to produce the
headline metrics — which high emitters have no P2 plan, and how
emissions are trending per facility over the last 3 reported years.

Setup:
    pip install pandas sqlalchemy pyodbc pymongo

Run:
    export AZURE_SQL_SERVER=... AZURE_SQL_DATABASE=... AZURE_SQL_USERNAME=... AZURE_SQL_PASSWORD=...
    export MONGO_URI=...
    python reconcile_and_transform.py
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SERVER = os.environ.get("AZURE_SQL_SERVER", "<your-server>.database.windows.net")
DATABASE = os.environ.get("AZURE_SQL_DATABASE", "emissions-analytics")
USERNAME = os.environ.get("AZURE_SQL_USERNAME", "<your-username>")
PASSWORD = os.environ.get("AZURE_SQL_PASSWORD", "<your-password>")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")

CONN_STR = (
    f"mssql+pyodbc://{USERNAME}:{PASSWORD}@{SERVER}:1433/{DATABASE}"
    "?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
)


def fetch_facility_and_emissions(engine):
    facilities = pd.read_sql("SELECT * FROM dbo.dim_facility", engine)
    gas = pd.read_sql("SELECT facility_id, year, quantity_co2e_tonnes FROM dbo.fact_emissions_by_gas", engine)

    # total CO2e per facility per year, summed across gas types
    yearly_totals = gas.groupby(["facility_id", "year"], as_index=False)["quantity_co2e_tonnes"].sum()
    return facilities, yearly_totals


def compute_trend(yearly_totals: pd.DataFrame) -> pd.DataFrame:
    """Latest reported year's total, and % change vs. 3 years prior, per facility.

    Real GHGRP data includes facilities with a near-zero reported year
    (temporary shutdown, partial-year operation, reporting gap) sitting
    right at the 3-years-prior mark -- e.g. Bridgewater Plant (NS tire
    manufacturing) reported 67.8 tonnes CO2e in 2021 against a normal
    15,000-27,000 tonne range in every surrounding year, which turns an
    unremarkable facility into a +23,000% "trend" if taken at face value.
    trend_baseline_flag marks these so a dashboard/report can visually
    separate "real growth" from "artifact of a weird base year" rather
    than silently reporting a misleading number.
    """
    results = []
    for facility_id, group in yearly_totals.groupby("facility_id"):
        group = group.sort_values("year")
        latest = group.iloc[-1]
        three_yr_prior = group[group["year"] <= latest["year"] - 3]
        trend_pct = None
        baseline_flag = None
        if not three_yr_prior.empty and three_yr_prior.iloc[-1]["quantity_co2e_tonnes"]:
            base = three_yr_prior.iloc[-1]["quantity_co2e_tonnes"]
            trend_pct = round((latest["quantity_co2e_tonnes"] - base) / base * 100, 2)
            facility_max = group["quantity_co2e_tonnes"].max()
            if facility_max and base < 0.01 * facility_max:
                baseline_flag = "low_base"
        results.append(
            {
                "facility_id": facility_id,
                "latest_year": int(latest["year"]),
                "latest_year_co2e_tonnes": latest["quantity_co2e_tonnes"],
                "three_year_emissions_trend_pct": trend_pct,
                "trend_baseline_flag": baseline_flag,
            }
        )
    return pd.DataFrame(results)


def fetch_mongo_p2_summary():
    """Mongo holds a boolean-flag document per facility-year (see
    load_to_mongo.py's docstring for why -- NPRI's real bulk data has no
    itemized P2 activity list to nest, just hasP2Plan/hasP2Activity).
    Take each facility's most recent reported year's flags."""
    client = MongoClient(MONGO_URI)
    collection = client["emissions_analytics"]["facility_p2_activities"]

    pipeline = [
        {"$match": {"facility_id": {"$ne": None}}},
        {"$sort": {"year": -1}},
        {
            "$group": {
                "_id": "$facility_id",
                "has_p2_plan": {"$first": "$has_p2_plan"},
                "has_p2_activity": {"$first": "$has_p2_activity"},
            }
        },
    ]
    docs = list(collection.aggregate(pipeline))
    df = pd.DataFrame(docs).rename(columns={"_id": "facility_id"})
    return df


def main():
    engine = create_engine(CONN_STR, fast_executemany=True)

    facilities, yearly_totals = fetch_facility_and_emissions(engine)
    trend = compute_trend(yearly_totals)
    p2_summary = fetch_mongo_p2_summary()

    enriched = facilities.merge(trend, on="facility_id", how="left")
    enriched = enriched.merge(p2_summary, on="facility_id", how="left")
    enriched["has_p2_plan"] = enriched["has_p2_plan"].fillna(False).astype(int)
    enriched["has_p2_activity"] = enriched["has_p2_activity"].fillna(False).astype(int)

    cols = [
        "facility_id", "facility_name", "province", "naics_description",
        "latest_year", "latest_year_co2e_tonnes", "three_year_emissions_trend_pct",
        "trend_baseline_flag", "has_p2_plan", "has_p2_activity",
    ]
    enriched = enriched[cols]

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dbo.fact_facility_enriched"))
    enriched.to_sql("fact_facility_enriched", engine, if_exists="append", index=False, chunksize=1000)

    flagged = enriched[enriched["trend_baseline_flag"] == "low_base"]
    if len(flagged) > 0:
        print(f"note: {len(flagged)} facility(ies) flagged trend_baseline_flag='low_base' -- their 3-year-prior "
              "baseline is under 1% of their own peak year, so the trend % reflects a reporting anomaly, not real "
              f"growth: {', '.join(flagged['facility_name'].tolist())}")

    # print the headline finding right away
    top_emitters = enriched[enriched["latest_year_co2e_tonnes"] >= 100000]
    no_plan = top_emitters[top_emitters["has_p2_plan"] == 0]
    if len(top_emitters) > 0:
        pct = round(len(no_plan) / len(top_emitters) * 100, 1)
        print(f"\nHEADLINE FINDING: {len(no_plan)} of {len(top_emitters)} top-emitting facilities "
              f"(100kt+ CO2e/year) — {pct}% — have no documented pollution prevention plan.\n")

    print(f"reconciled {len(enriched)} facilities -> dbo.fact_facility_enriched")


if __name__ == "__main__":
    main()
