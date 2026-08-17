# Azure Data Factory orchestration (design, not deployed)

```
Pipeline: pl_emissions_analytics

1. Manual, outside ADF: download GHGRP + NPRI CSVs, run
   data_prep/clean_and_prepare.py. Neither open-data portal exposes an
   API stable enough for a Copy activity's HTTP source, so this stays a
   scheduled script rather than a native connector.

2. Copy Activity: cleaned CSVs (Blob Storage) -> dim_facility,
   fact_emissions_by_gas, fact_emissions_by_source in Azure SQL.

3. Azure Function Activity: MongoDB load of P2 activity documents
   (wraps load_to_mongo.py).

4. Azure Function Activity: reconciliation (wraps
   reconcile_and_transform.py; runs after 2 and 3 both succeed).

5. Schedule trigger: GHGRP/NPRI publish annually, so a monthly or
   quarterly trigger matches the source data's real cadence.
```

## Setup

1. Upload cleaned CSVs from `data/clean/` to a Blob Storage container.
2. Create linked services for Blob Storage and Azure SQL.
3. Create datasets for each clean CSV and its SQL sink table.
4. Build the Copy Data activity, run once in debug mode, confirm rows
   land in `dbo.dim_facility` etc.
5. Package `load_to_mongo.py` and `reconcile_and_transform.py` as
   HTTP-triggered Azure Functions, add them as pipeline activities.
6. Add the schedule trigger.

## Cost

Azure SQL's serverless tier and Azure Functions' consumption plan keep
this near-free if resources are paused between demos. MongoDB Atlas M0
is free indefinitely.
