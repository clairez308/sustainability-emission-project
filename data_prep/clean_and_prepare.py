"""
Cleans the raw downloaded government files into the shape the loaders
expect. This is the only script that touches the messy real-world files
directly -- everything downstream (etl/load_to_sql.py,
etl/load_to_mongo.py) reads the clean output this produces.

Before running:
    1. Download the two GHGRP files (Emissions by Gas, Emissions by
       Source) as CSV. The open.canada.ca dataset page only links to a
       search tool, not a static file -- the real bulk CSVs are behind
       its "Go to resource" link, on ECCC's data catalogue:
       https://open.canada.ca/data/en/dataset/a8ba14b7-7f23-462a-bdbb-83b0ef629823
       -> "Summary of GHG Emissions by Facility (EN)" -> Go to resource
       -> data-donnees.ec.gc.ca/.../greenhouse-gas-reporting-program-.../
       Save as data/raw/ghgrp_emissions_by_gas.csv and
       data/raw/ghgrp_emissions_by_source.csv.

    2. Fetch the NPRI pollution-prevention data. There is no
       downloadable P2 CSV -- run `node data_prep/fetch_npri.js
       data/raw/npri_pollution_prevention.csv`, which pages through
       pollution-waste.canada.ca's facility search API and writes a
       flat facility-year CSV with hasP2Plan/hasP2Activity booleans
       (see the note in config.py for why it's booleans, not an
       itemized activity list).

    3. Open each file's first row and check it against
       data_prep/config.py -- update the column-name mapping there if
       the real headers differ from what's assumed.

Run:
    pip install pandas
    python clean_and_prepare.py
"""

import re
from pathlib import Path

import pandas as pd

from config import (
    GHGRP_GAS_COLUMNS,
    GHGRP_GAS_MELT_COLUMNS,
    GHGRP_SOURCE_COLUMNS,
    NPRI_P2_COLUMNS,
    SOURCE_CATEGORY_LABELS,
    LEGAL_SUFFIXES_TO_STRIP,
)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
CLEAN_DIR = Path(__file__).resolve().parent.parent / "data" / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

# The real GHGRP CSVs are UTF-8 with a BOM; the NPRI CSV (produced by
# fetch_npri.js) is plain UTF-8. utf-8-sig handles both -- it strips a
# BOM if present and is a no-op if not.
CSV_ENCODING = "utf-8-sig"


def normalize_facility_name(name: str) -> str:
    """Lowercase, strip legal suffixes and punctuation, collapse whitespace --
    used as the fallback join key between GHGRP and NPRI for facilities
    that don't have a shared NPRI ID on both sides."""
    if not isinstance(name, str):
        return ""
    n = name.lower().strip()
    n = re.sub(r"[.,]", "", n)
    for suffix in LEGAL_SUFFIXES_TO_STRIP:
        n = re.sub(rf"\b{re.escape(suffix)}\b", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _check_columns(df: pd.DataFrame, column_map: dict, filename: str) -> None:
    missing = [v for v in column_map.values() if v not in df.columns]
    if missing:
        raise ValueError(
            f"{filename}: expected columns not found: {missing}\n"
            "Check the file's real header row and update data_prep/config.py"
        )


def _clean_npri_id(series: pd.Series) -> pd.Series:
    """GHGRP uses 0 as a sentinel for "no NPRI ID on file", not a real ID --
    treat it as missing so it doesn't collide every facility that has no
    crosswalk ID into one bucket."""
    ids = pd.to_numeric(series, errors="coerce").astype("Int64")
    return ids.mask(ids == 0)


def clean_ghgrp():
    gas_raw = pd.read_csv(RAW_DIR / "ghgrp_emissions_by_gas.csv", low_memory=False, encoding=CSV_ENCODING)
    _check_columns(gas_raw, GHGRP_GAS_COLUMNS, "ghgrp_emissions_by_gas.csv")
    for cols in GHGRP_GAS_MELT_COLUMNS.values():
        for col in (cols["tonnes"], cols["co2e"]):
            if col and col not in gas_raw.columns:
                raise ValueError(f"ghgrp_emissions_by_gas.csv: expected gas column not found: {col}")

    ids = gas_raw.rename(columns={v: k for k, v in GHGRP_GAS_COLUMNS.items()})[list(GHGRP_GAS_COLUMNS.keys())].copy()
    ids["year"] = pd.to_numeric(ids["year"], errors="coerce").astype("Int64")
    ids["npri_id"] = _clean_npri_id(ids["npri_id"])

    # Facility identity: dedupe on ghgrp_id, ECCC's own stable ID for a
    # reporting facility, NOT on normalized facility name. Real facilities
    # get renamed over a 20-year reporting history (ownership changes,
    # rebranding, formatting drift) -- e.g. "Sundance Generating Plant" and
    # "Sundance Thermal Electric Power Generating Plant" are the same
    # Alberta plant (same ghgrp_id, same npri_id) under two names used in
    # different years. Deduping by normalized name instead of ghgrp_id was
    # silently splitting ~600 real facilities (21% of them) across multiple
    # facility_id rows, which fragmented their emissions history (breaking
    # the 3-year trend calc) and caused the NPRI join to miss whichever
    # fragment didn't carry the crosswalk ID -- inflating the "no P2 plan"
    # headline count with facilities that were actually just unmatched.
    # Keep the most recent year's name/NPRI ID/NAICS per ghgrp_id: it's the
    # most current, and early years are more likely to be missing the NPRI
    # ID crosswalk than later ones.
    ids_by_recency = ids.sort_values("year", ascending=False)
    dim_facility = (
        ids_by_recency[["ghgrp_id", "facility_name", "npri_id", "province", "naics_code", "naics_description"]]
        .drop_duplicates(subset="ghgrp_id", keep="first")
        .reset_index(drop=True)
    )
    dim_facility.insert(0, "facility_id", range(1, len(dim_facility) + 1))

    n_name_variants = len(ids["facility_name"].unique()) - len(dim_facility)
    if n_name_variants > 0:
        print(f"note: consolidated {n_name_variants} historical facility-name variants down to "
              f"{len(dim_facility)} distinct facilities (deduped by ghgrp_id, not name)")

    ghgrp_id_to_facility_id = dict(zip(dim_facility["ghgrp_id"], dim_facility["facility_id"]))
    ids["facility_id"] = ids["ghgrp_id"].map(ghgrp_id_to_facility_id)

    # facility_key (normalized name) is still needed as a *fallback* join
    # key for NPRI rows that have no npri_id crosswalk from GHGRP at all
    dim_facility["facility_key"] = dim_facility["facility_name"].apply(normalize_facility_name)
    key_to_id = dict(zip(dim_facility["facility_key"], dim_facility["facility_id"]))

    # melt the wide per-gas columns into one row per (facility, year, gas_type)
    melted = []
    for gas_type, cols in GHGRP_GAS_MELT_COLUMNS.items():
        frame = ids[["facility_id", "year"]].copy()
        frame["gas_type"] = gas_type
        frame["quantity_tonnes"] = (
            pd.to_numeric(gas_raw[cols["tonnes"]], errors="coerce") if cols["tonnes"] else pd.NA
        )
        # CO2 has no separate CO2e column: its GWP is 1, so tonnes == tonnes CO2e
        frame["quantity_co2e_tonnes"] = (
            pd.to_numeric(gas_raw[cols["co2e"]], errors="coerce") if cols["co2e"] else frame["quantity_tonnes"]
        )
        melted.append(frame)
    gas = pd.concat(melted, ignore_index=True)
    # most facilities only emit a subset of the six gas categories --
    # dropping the zero/blank ones is expected, not a data-quality bug
    gas = gas[gas["quantity_co2e_tonnes"].notna() & (gas["quantity_co2e_tonnes"] != 0)].reset_index(drop=True)

    source_raw = pd.read_csv(RAW_DIR / "ghgrp_emissions_by_source.csv", low_memory=False, encoding=CSV_ENCODING)
    _check_columns(source_raw, GHGRP_SOURCE_COLUMNS, "ghgrp_emissions_by_source.csv")
    source = source_raw.rename(columns={v: k for k, v in GHGRP_SOURCE_COLUMNS.items()})[
        list(GHGRP_SOURCE_COLUMNS.keys())
    ].copy()
    source["year"] = pd.to_numeric(source["year"], errors="coerce").astype("Int64")
    source["quantity_co2e_tonnes"] = pd.to_numeric(source["quantity_co2e_tonnes"], errors="coerce")
    source["source_category"] = source["source_category"].map(SOURCE_CATEGORY_LABELS).fillna(source["source_category"])
    # join on ghgrp_id (both files carry it) rather than normalized name --
    # see the note in clean_ghgrp() on why name-matching fragments facilities
    source["facility_id"] = source["ghgrp_id"].map(ghgrp_id_to_facility_id)
    unmatched_source = source["facility_id"].isna().sum()
    if unmatched_source:
        print(f"note: {unmatched_source}/{len(source)} Emissions-by-Source rows didn't match a facility "
              "from the Emissions-by-Gas file by ghgrp_id -- dropped")
    source = source.dropna(subset=["facility_id"]).reset_index(drop=True)

    # A small number of real rows have a blank "Emission Source" AND a blank
    # quantity -- an empty placeholder row in ECCC's export with zero
    # informational content (the facility's total emissions are still
    # captured via fact_emissions_by_gas). Dropping is correct, not just
    # convenient: source_category is NOT NULL in the SQL schema, and there's
    # no real category to assign these to.
    blank_category = source["source_category"].isna()
    if blank_category.any():
        print(f"note: dropped {blank_category.sum()} Emissions-by-Source rows with a blank source category "
              "and no quantity in the real ECCC export")
        source = source[~blank_category].reset_index(drop=True)

    dim_facility.drop(columns="facility_key").to_csv(CLEAN_DIR / "dim_facility.csv", index=False)
    gas.to_csv(CLEAN_DIR / "fact_emissions_by_gas.csv", index=False)
    source.drop(columns=["facility_name", "province", "npri_id", "ghgrp_id"]).to_csv(
        CLEAN_DIR / "fact_emissions_by_source.csv", index=False
    )
    print(f"cleaned {len(dim_facility)} facilities, {len(gas)} gas rows, {len(source)} source rows")
    return dim_facility, key_to_id


def clean_npri(dim_facility: pd.DataFrame, key_to_id: dict):
    npri = pd.read_csv(RAW_DIR / "npri_pollution_prevention.csv", low_memory=False, encoding=CSV_ENCODING)
    _check_columns(npri, NPRI_P2_COLUMNS, "npri_pollution_prevention.csv")
    npri = npri.rename(columns={v: k for k, v in NPRI_P2_COLUMNS.items()})[list(NPRI_P2_COLUMNS.keys())]

    before = len(npri)
    npri = npri.drop_duplicates().reset_index(drop=True)
    if before != len(npri):
        print(f"note: dropped {before - len(npri)} exact-duplicate rows from npri_pollution_prevention.csv "
              "(the facility-search API returns overlapping pages on large paged queries)")

    npri["year"] = pd.to_numeric(npri["year"], errors="coerce").astype("Int64")
    npri["npri_id"] = _clean_npri_id(npri["npri_id"])
    npri["facility_key"] = npri["facility_name"].apply(normalize_facility_name)

    npri_id_to_facility_id = (
        dim_facility.dropna(subset=["npri_id"]).drop_duplicates(subset="npri_id").set_index("npri_id")["facility_id"]
    ).to_dict()

    npri["facility_id"] = npri["npri_id"].map(npri_id_to_facility_id)
    matched_by_id = npri["facility_id"].notna().sum()

    fallback = npri["facility_id"].isna()
    npri.loc[fallback, "facility_id"] = npri.loc[fallback, "facility_key"].map(key_to_id)
    matched_total = npri["facility_id"].notna().sum()

    print(f"matched {matched_total}/{len(npri)} NPRI rows to a GHGRP facility_id "
          f"({matched_by_id} by NPRI-ID crosswalk, {matched_total - matched_by_id} by normalized-name fallback)")
    print("Unmatched rows are kept (facility_id will be null) -- they're NPRI-only facilities")
    print("below the GHGRP reporting threshold, which is itself worth a sentence in your writeup.")

    npri.drop(columns=["facility_key", "ghgrp_id", "facility_name", "province", "naics_code"]).to_csv(
        CLEAN_DIR / "npri_p2_activities.csv", index=False
    )
    return npri


def main():
    dim_facility, key_to_id = clean_ghgrp()
    clean_npri(dim_facility, key_to_id)


if __name__ == "__main__":
    main()
