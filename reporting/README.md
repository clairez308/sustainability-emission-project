# Paginated report

`TopEmittersP2Gap.rdl` — a "Top Emitters — Pollution Prevention Gap"
report over `dbo.vw_p2_gap_analysis`, filtered to
`emitter_tier = 'Top emitter (100kt+)'`. Landscape Tablix, grouped by
province, detail rows sorted by `latest_year_co2e_tonnes` descending.
Columns: facility name, sector, latest-year CO2e, has P2 plan, has P2
activity. The province column shows once as the group header rather
than repeating on every row.

A `Province` multi-value parameter (default: all provinces selected,
backed by a small `ProvinceList` dataset) lets the report run for a
single jurisdiction — a realistic ask for a client-facing operational
report.

`TopEmittersP2Gap.xlsx` is an exported snapshot of the report's output.

## Deployment

Deployed to a local Power BI Report Server (Developer edition — free,
non-expiring):

- Catalog database on the local SQL Server Express instance
  (`SQLEXPRESS`), separate from `emissions-analytics`, which stays on
  Azure SQL as the report's actual data source.
- Web portal: `http://localhost/reports/browse/EmissionsAnalytics`
- Published via PowerShell (`ReportingServicesTools`): `New-RsFolder`
  to create `/EmissionsAnalytics`, then `Write-RsCatalogItem` to
  publish the `.rdl`.
- The data source prompts for credentials at run time rather than
  storing them — consistent with this repo never committing connection
  strings or passwords. To run without a prompt, set stored credentials
  directly in the web portal under the report's Manage → Data Sources.

## Running it yourself

Open `TopEmittersP2Gap.rdl` in Report Builder (or SSDT), point
`EmissionsAnalyticsDataSource`'s connection string at your own Azure
SQL server, and Run.
