# SSRS paginated report

Build a "Top Emitters — Pollution Prevention Gap" paginated report over
`dbo.vw_p2_gap_analysis`, filtered to `emitter_tier = 'Top emitter
(100kt+)'`, sorted by `latest_year_co2e_tonnes` descending.

**Columns**: facility_name, province, naics_description,
latest_year_co2e_tonnes, has_p2_plan, has_p2_activity.

Standard Tablix layout: group by province, sort by
`latest_year_co2e_tonnes` descending within each group.

**Report parameter to add**: a Province multi-select parameter, so the
report can be run for a specific jurisdiction — a realistic ask for a
client-facing operational report.

## Implementation

`TopEmittersP2Gap.rdl` in this folder implements the above: landscape
layout, Tablix grouped by province (group header row + detail rows
sorted by `latest_year_co2e_tonnes` descending within each group), and
the `Province` multi-value parameter (default: all provinces selected),
backed by a small `ProvinceList` dataset for its valid/default values.

Before running it:
1. Open in Report Builder (or SSDT/Visual Studio's Report Designer) —
   it was authored by hand as XML, not exported from the designer, so
   give it a look before deploying.
2. Update the `EmissionsAnalyticsDataSource` connection string
   (`Data Source=your-server.database.windows.net;...`) to point at
   the real Azure SQL server from your `.env`. No credentials are
   embedded — the data source prompts for them at run time by design,
   consistent with this repo's "never commit connection strings/
   passwords" rule.
3. The province column isn't repeated per detail row — it's shown once
   as the group header band, to avoid redundant repetition down the
   table. If you'd rather see it as a literal column too, that's a
   quick change in Report Builder.
