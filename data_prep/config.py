"""
Column-name mapping for the raw downloaded files, verified against the
real files downloaded 2026-07-24 from:
  - GHGRP: data-donnees.ec.gc.ca (ECCC Data Catalogue), via the
    open.canada.ca dataset a8ba14b7-7f23-462a-bdbb-83b0ef629823
    ("Go to resource" -> the actual bulk CSVs, not the search-tool page).
  - NPRI: pollution-waste.canada.ca/national-release-inventory/, the
    facility data search tool's JSON API. There is no bulk downloadable
    P2 CSV -- see the note on NPRI_P2_COLUMNS below.

Government open-data files occasionally rename or reorder columns
between publication years. If a script raises "expected columns not
found", re-check the real header row (`head -1 file.csv` after forcing
UTF-8) and update the right-hand values below. Nothing else in
data_prep/ or etl/ should need to change for a pure rename.

Encoding note: the two GHGRP CSVs are UTF-8 with a BOM. The NPRI CSV
(built by fetch_npri.js from the search API, not downloaded directly)
is plain UTF-8. clean_and_prepare.py opens all three with
encoding="utf-8-sig" so the BOM doesn't leak into the first column name.
"""

# --- GHGRP: Emissions by Gas file (PDGES-GHGRP-GHGEmissionsGES-2004-Present.csv) ---
# One row per facility per year, wide: a separate tonnes/CO2e column pair
# per gas species (not the long facility x year x gas_type shape this
# project originally assumed -- clean_and_prepare.py melts it into that
# shape). Only the columns actually used downstream are mapped here;
# the ~20 administrative columns (company legal/trade name, DUNS,
# public contact block) are present in the real file but dropped.
GHGRP_GAS_COLUMNS = {
    "ghgrp_id": "GHGRP ID No. / No d'identification du PDGES",
    "year": "Reference Year / Année de référence",
    "facility_name": "Facility Name / Nom de l'installation",
    "province": "Facility Province or Territory / Province ou territoire de l'installation",
    "npri_id": "Facility NPRI ID / Numéro d'identification de l'INRP",
    "naics_code": "Facility NAICS Code / Code SCIAN de l'installation",
    "naics_description": "English Facility NAICS Code Description / Description du code SCIAN de l'installation en anglais",
}

# Per-gas columns to melt into one row per (facility, year, gas_type).
# HFC and PFC are reported as ~13 and ~7 individual species respectively
# (different tonnes are not comparable across species), so those two
# collapse to their pre-computed "Total (tonnes CO2e)" column only --
# quantity_tonnes is left null for HFC/PFC rows. CO2 has no separate
# CO2e column because CO2's GWP is 1 (tonnes == tonnes CO2e).
GHGRP_GAS_MELT_COLUMNS = {
    "CO2": {"tonnes": "CO2 (tonnes)", "co2e": None},
    "CH4": {"tonnes": "CH4 (tonnes)", "co2e": "CH4 (tonnes CO2e / tonnes éq. CO2)"},
    "N2O": {"tonnes": "N2O (tonnes)", "co2e": "N2O (tonnes CO2e / tonnes éq. CO2)"},
    "HFC": {"tonnes": None, "co2e": "HFC Total (tonnes CO2e / tonnes éq. CO2)"},
    "PFC": {"tonnes": None, "co2e": "PFC Total (tonnes CO2e / tonnes éq. CO2)"},
    "SF6": {"tonnes": "SF6 (tonnes)", "co2e": "SF6 (tonnes CO2e / tonnes éq. CO2)"},
}
GHGRP_GAS_TOTAL_COLUMN = "Total Emissions (tonnes CO2e) / Émissions totales (tonnes éq. CO2) - excl. CO2bio"

# --- GHGRP: Emissions by Source file (PDGES-GHGRP-GHGEmissionsSourcesGES-2022-Present.csv) ---
# One row per facility per year per source category -- this one already
# matches the long shape the rest of the pipeline expects. Same admin
# columns as the Gas file, plus "Emission Source" and per-source totals.
GHGRP_SOURCE_COLUMNS = {
    "ghgrp_id": "GHGRP ID No. / No d'identification du PDGES",
    "year": "Reference Year / Année de référence",
    "facility_name": "Facility Name / Nom de l'installation",
    "province": "Facility Province or Territory / Province ou territoire de l'installation",
    "npri_id": "Facility NPRI ID / Numéro d'identification de l'INRP",
    "source_category": "Emission Source / Source d'emission",
    "quantity_co2e_tonnes": "Total Emissions from Source (tonnes CO2e) / Émissions totales de la Source (tonnes éq. CO2)  - excl. CO2bio",
}

# The raw "Emission Source" values are internal codes, not display names.
SOURCE_CATEGORY_LABELS = {
    "EC_GeneralStationaryCombustionEmissions": "Stationary Fuel Combustion",
    "EC_IndustrialProcessEmissions": "Industrial Process",
    "EC_OnSiteTransportationEmissions": "On-site Transportation",
    "EC_WasteEmissions": "Waste",
    "EC_WastewaterEmissions": "Wastewater",
    "EC_VentingEmissions": "Fugitives (Venting)",
    "EC_FlaringEmissions": "Fugitives (Flaring)",
    "EC_FugitiveEmissions": "Fugitives (Leakage)",
    "EC_CO2BiomassCombustion": "CO2 from Biomass Combustion",
}

# --- NPRI: Pollution Prevention data ---
# README/original design assumed a downloadable CSV with an itemized,
# variable-length list of P2 activities per facility (category,
# description, barrier). That file does not exist as public bulk data.
# The real source is pollution-waste.canada.ca's facility search tool;
# its bulk JSON export only carries two booleans per facility-year:
# hasP2Plan and hasP2Activity. The per-facility detail API does expose
# an itemized `p2Plan.activityCategories` array in principle, but it
# came back empty on every facility sampled (including ones flagged
# hasActivities=true) -- so it isn't usable as a data source right now.
# Scope scaled down accordingly: MongoDB gets a boolean-flag document
# per facility-year rather than a nested activity list. This still
# fully supports the headline finding (% of top emitters with no P2
# plan), which only needs hasP2Plan.
#
# This CSV is produced by scripts/fetch_npri.js (not hand-downloaded --
# there's no static file to save), which writes these exact column
# names, so this mapping is an identity map.
NPRI_P2_COLUMNS = {
    "npri_id": "npri_id",
    "ghgrp_id": "ghgrp_id",
    "year": "year",
    "facility_name": "facility_name",
    "province": "province",
    "naics_code": "naics_code",
    "has_p2_plan": "has_p2_plan",
    "has_p2_activity": "has_p2_activity",
}

# Facility-name normalization: government CSVs are inconsistent about
# casing, punctuation, and legal suffixes (Inc./Ltd./Ltée). Used by
# etl/reconcile_and_transform.py as a *fallback* join between GHGRP and
# NPRI. The primary join key is the NPRI ID: GHGRP's file carries a
# "Facility NPRI ID" column, and NPRI's own records carry a matching
# npri_id, so most facilities can be joined on that shared ID directly
# -- name matching is only needed for the rows where that crosswalk is
# missing on one side.
LEGAL_SUFFIXES_TO_STRIP = ["inc.", "inc", "ltd.", "ltd", "ltee", "ltée", "corp.", "corp", "llc"]
