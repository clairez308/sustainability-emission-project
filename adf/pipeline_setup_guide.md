# Wiring this into Azure Data Factory

## Pipeline structure

```
Pipeline: pl_emissions_analytics
│
├── 1. (Manual, outside ADF) Download GHGRP + NPRI CSVs, run data_prep/clean_and_prepare.py
│      Government open-data portals here don't expose a stable API endpoint
│      suitable for a Copy activity's HTTP source, so this step stays a
│      documented manual/scheduled script rather than a native connector —
│      worth stating plainly rather than forcing a fake "API integration"
│      into the design.
│
├── 2. Copy Activity: cleaned CSVs (Blob Storage) → dim_facility, fact_emissions_by_gas,
│      fact_emissions_by_source in Azure SQL Database
│      (ADF UI Copy Data wizard — no code)
│
├── 3. Azure Function Activity: trigger MongoDB load of P2 activity documents
│      (wraps load_to_mongo.py)
│
├── 4. Azure Function Activity: reconciliation
│      (wraps reconcile_and_transform.py; dependency = Succeeded on both 2 and 3)
│
└── 5. Trigger: Schedule trigger — GHGRP/NPRI publish annually, so a
       monthly or quarterly trigger is more honest here than "daily";
       explain in your README that the cadence matches the source data's
       actual publication frequency rather than defaulting to daily for
       its own sake.
```

## Steps in the Azure Portal

1. Upload the cleaned CSVs from `data/clean/` to a Blob Storage
   container (e.g. `clean/emissions/`).
2. Create linked services for Blob Storage and Azure SQL Database.
3. Create datasets for each clean CSV and the corresponding SQL sink
   tables.
4. Build the Copy Data activity, run once in debug mode to confirm rows
   land in `dbo.dim_facility` etc.
5. Package `load_to_mongo.py` and `reconcile_and_transform.py` as
   HTTP-triggered Azure Functions, deploy, then add two "Azure Function"
   activities to the pipeline with dependency arrows set to "Success."
6. Add a Schedule trigger matched to the real data's publication cadence
   (annual GHGRP/NPRI releases — quarterly re-runs are more than enough
   to demonstrate the automation without implying daily-fresh data that
   doesn't exist).
7. Export the pipeline as an ARM template for your repo/portfolio.

## Cost note

Same as before — Azure SQL Database's serverless tier and Azure
Functions' consumption plan keep this close to free if resources are
paused/torn down between demos. MongoDB Atlas M0 is free indefinitely.
