# Canadian Industrial Emissions & Pollution Prevention Analytics

An analytics pipeline built on **real, public Government of Canada
data** — facility-level greenhouse gas emissions joined against
facility-level pollution prevention (P2) activity, to answer a genuinely
useful sustainability question: *which high-emitting facilities have no
documented pollution prevention plan, and how are emissions trending by
sector and province?*

This is not a synthetic dataset exercise. Every number in the final
dashboard traces back to a facility that actually reported to the
Government of Canada under legislated reporting requirements (CEPA
1999), and the headline finding below was spot-checked by hand against
the raw source files before being trusted.

## The two real data sources

### 1. Greenhouse Gas Reporting Program (GHGRP) — structured, → Azure SQL

Facilities emitting 10,000+ tonnes CO2e/year must report annually to
Environment and Climate Change Canada. Two files, both real:

- **Emissions by Gas** (2004–present): facility × year × gas type
  (CO2, CH4, N2O, HFC, PFC, SF6), in tonnes and tonnes CO2 eq.
- **Emissions by Source** (2022–present): facility × year × source
  category (Stationary Fuel Combustion, Industrial Process, On-site
  Transportation, Waste, Wastewater, Fugitives, biomass CO2).

**Download**: https://open.canada.ca/data/en/dataset/a8ba14b7-7f23-462a-bdbb-83b0ef629823
(select the .csv format for each of the two files listed above; column
headers are documented in the accompanying "Lisez Moi – Read Me" tab —
check these against `data_prep/config.py` since exact header names can
shift slightly year to year).

### 2. National Pollutant Release Inventory (NPRI) — Pollution Prevention data, → MongoDB

For each reporting facility, NPRI's public facility-search API exposes
two per-year flags: whether a formal P2 plan exists (`hasP2Plan`) and
whether any P2 activity was undertaken (`hasP2Activity`). There is no
downloadable bulk CSV, and the itemized category-level detail
(material/feedstock substitution, equipment modification, etc.) that
NPRI's own site references is not populated in the API's per-facility
response — so this pipeline scopes to the two boolean flags, fetched via
`data_prep/fetch_npri.js` paging through the search API. MongoDB stores
one flat document per facility-year; still a legitimate document-store
fit (schema-light, no relational join needed at write time), just a
smaller shape than a first pass at the dataset descriptions suggested.

**Source**: https://www.canada.ca/en/environment-climate-change/services/national-pollutant-release-inventory/tools-resources-data.html
→ "Explore National Pollutant Release Inventory Data"

## Why these two together

GHGRP tells you *how much* a facility emits. NPRI's P2 data tells you
*whether a facility has a documented plan for doing something about it*.
Neither dataset alone answers the interesting question; joined, you can
ask things like:

- What share of the highest-emitting facilities have no P2 plan at all?
- Which sectors (by NAICS code, present in both datasets) are furthest
  behind?
- How is each facility's emissions trending year over year, and does
  that correlate with having a P2 plan in place?

These are exactly the kind of gap-analysis questions a sustainability
consulting engagement produces for a client.

## Pipeline

1. `data_prep/` — cleans and standardizes the raw downloaded CSVs into
   the shape the loaders expect. Facility identity is resolved by
   `ghgrp_id` (ECCC's own stable ID), with normalized-name matching used
   only as a fallback for the NPRI join where no ID crosswalk exists —
   see **Data quality** below for why that distinction mattered.
2. `sql/` — Azure SQL Database schema: `dim_facility`,
   `fact_emissions_by_gas`, `fact_emissions_by_source`, and the
   reconciled `fact_facility_enriched` table, plus reporting views.
3. `etl/load_to_sql.py` — loads cleaned emissions data to Azure SQL.
4. `etl/load_to_mongo.py` — loads the P2 flag documents to MongoDB.
5. `etl/reconcile_and_transform.py` — joins facilities across both
   sources (GHGRP ID / NPRI ID crosswalk, with normalized-name fallback)
   and computes `has_p2_plan`, `has_p2_activity`, and each facility's
   3-year emissions trend.
6. `adf/` — orchestration guide.
7. `powerbi/`, `reporting/` — dashboard and paginated report guides.

See `diagrams/architecture.md` for the visual.

## Headline finding

Of the **408 facilities** reporting 100,000+ tonnes CO2e in their most
recent year, **331 (81.1%)** have no NPRI-documented P2 plan. Restricting
to only the facilities with a confirmed NPRI record (excluding 40 top
emitters — mostly gas pipeline/transmission systems — that have no NPRI
record under either their GHGRP crosswalk ID or a name match, a genuine
data gap rather than a confirmed "no plan"), the figure is **291 of 368
(79.1%)**. Both numbers tell the same story; the second is the more
defensible one to quote without a footnote.

## Data quality: real issues found and fixed

Cleaning and reconciling the actual downloaded files (not just their
documented structure) surfaced several real problems, each caught by
running the pipeline end-to-end and spot-checking results against the
raw source data rather than trusting the first successful run:

- **Facility identity was fragmented by name, not ID.** The original
  join logic deduplicated facilities by normalized facility name. Real
  facilities get renamed over a 20-year reporting history — e.g.
  "Sundance Generating Plant" and "Sundance Thermal Electric Power
  Generating Plant" are the same Alberta plant (same `ghgrp_id`, same
  NPRI ID) reported under different names in different years. This
  silently split 606 real facilities (21% of the total) across multiple
  rows, fragmenting their emissions history and causing the NPRI join to
  miss whichever name-variant didn't carry the ID crosswalk. Fixed by
  deduplicating on `ghgrp_id` instead, which dropped the "no NPRI match"
  rate among top emitters from 45.6% to 9.8% and moved the headline
  number from an overstated 89.0% to a verified 81.1%.
- **NPRI's real bulk data is boolean flags, not an itemized activity
  list** — see the NPRI section above. Discovered only after actually
  fetching the data; the loader, reconciliation script, and SQL schema
  were all built against the richer shape and had to be scaled back to
  match reality.
- **80 rows in the real Emissions-by-Source file are empty placeholders**
  (blank source category *and* blank quantity) rather than a real
  category — dropped explicitly rather than allowed to violate the
  schema's `NOT NULL` constraint.
- **A single-year reporting anomaly can produce a nonsensical trend.**
  Bridgewater Plant (NS, tire manufacturing) reported 67.8 tonnes CO2e in
  2021 against a normal 15,000–27,000 tonne range in every surrounding
  year — likely a shutdown or reporting gap — which turned an
  unremarkable facility into a +23,000% "3-year trend" if taken at face
  value. `fact_facility_enriched.trend_baseline_flag` marks the 7
  facilities where this applies so a dashboard can separate real growth
  from a reporting artifact instead of silently showing a misleading
  number.

## Suggested resume bullets

- Built an Azure SQL Database + MongoDB analytics pipeline joining two
  real Government of Canada datasets (GHGRP facility emissions, NPRI
  pollution prevention data) covering 2,843 industrial facilities and
  62,000+ facility-year emissions records.
- Identified that 79% of top-emitting facilities (100kt+ CO2e/year) have
  no documented pollution prevention plan — verified by hand against
  the raw source data before reporting it.
- Found and fixed a facility-identity bug (deduplication by name instead
  of stable ID) that had inflated the headline finding by ~8 points and
  fragmented 21% of facilities' emissions history; corrected it by
  keying identity to ECCC's own `ghgrp_id`.
- Orchestrated the pipeline in Azure Data Factory and surfaced results
  through Power BI and SSRS reporting.
