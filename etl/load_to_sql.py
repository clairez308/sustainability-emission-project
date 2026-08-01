"""
Loads the cleaned CSVs (produced by data_prep/clean_and_prepare.py)
into Azure SQL Database.

Setup:
    pip install pandas sqlalchemy pyodbc
    (also need the "ODBC Driver 18 for SQL Server" installed)

Before running:
    1. Run data_prep/clean_and_prepare.py first — this script expects
       data/clean/dim_facility.csv, fact_emissions_by_gas.csv,
       fact_emissions_by_source.csv to already exist.
    2. Run sql/01_schema.sql against your Azure SQL Database.
    3. Set the environment variables below.

Run:
    python load_to_sql.py
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CLEAN_DIR = Path(__file__).resolve().parent.parent / "data" / "clean"

SERVER = os.environ.get("AZURE_SQL_SERVER", "<your-server>.database.windows.net")
DATABASE = os.environ.get("AZURE_SQL_DATABASE", "emissions-analytics")
USERNAME = os.environ.get("AZURE_SQL_USERNAME", "<your-username>")
PASSWORD = os.environ.get("AZURE_SQL_PASSWORD", "<your-password>")

CONN_STR = (
    f"mssql+pyodbc://{USERNAME}:{PASSWORD}@{SERVER}:1433/{DATABASE}"
    "?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
)

TABLES = {
    "dim_facility.csv": "dim_facility",
    "fact_emissions_by_gas.csv": "fact_emissions_by_gas",
    "fact_emissions_by_source.csv": "fact_emissions_by_source",
}


def main():
    engine = create_engine(CONN_STR, fast_executemany=True)

    for csv_name, table_name in TABLES.items():
        path = CLEAN_DIR / csv_name
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found — run data_prep/clean_and_prepare.py first"
            )
        df = pd.read_csv(path)
        df.to_sql(table_name, engine, if_exists="append", index=False, chunksize=1000)
        print(f"loaded {len(df)} rows into dbo.{table_name}")


if __name__ == "__main__":
    main()
