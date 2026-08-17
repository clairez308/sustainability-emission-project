# Power BI dashboard

Connects to Azure SQL views: `vw_p2_gap_analysis`, `vw_sector_summary`,
`vw_province_summary`, `vw_emissions_trend_by_gas`. Built as a Power BI
Project (`.pbip` + `Report/`/`SemanticModel/` folders) rather than a
single `.pbix`, so changes are readable in a git diff instead of a
binary blob.

## Pages

- **National Overview** — KPI cards (facility count, latest-year CO2e,
  % of top emitters without a P2 plan), a province map colored by
  `pct_with_p2_plan`, and a trend line by gas type.
- **Sector View** — sector emissions bar chart, colored by
  `pct_with_p2_plan`. This is the chart the headline finding sits on.
- **Facility Drill-down** — a filterable table sortable by
  `three_year_emissions_trend_pct`, so both the worst performers and
  the ones genuinely improving are easy to find.

## Navigation

A bookmark-driven top nav bar replaces the default page tabs, and the
province / sector / emitter-tier / has-P2-plan slicers are synced
across all three pages via Power BI's Sync Slicers, so filtering
persists as you move between pages instead of resetting.

## Reusing this

`emissions dashboard.pbit` is a Power BI Template — the same report and
model with the data stripped out. Opening it prompts for a data source
instead of pointing at this project's Azure SQL instance, so it's the
quickest way to point this report layout at a different database
without rebuilding it from scratch.

## A framing note

The write-up sticks to descriptive statistics — counts, percentages,
trends — rather than naming or editorializing about specific
facilities. NPRI's own stated purpose is transparency and informing
pollution-prevention priorities, and that's the frame the dashboard
uses too.
