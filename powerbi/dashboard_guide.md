# Power BI dashboard

Connect to Azure SQL Database, pointing at `dbo.vw_p2_gap_analysis`,
`dbo.vw_sector_summary`, `dbo.vw_province_summary`, and
`dbo.vw_emissions_trend_by_gas`.

## Suggested DAX measures

```
Total Facilities = COUNTROWS(vw_p2_gap_analysis)

Total CO2e (latest year) = SUM(vw_p2_gap_analysis[latest_year_co2e_tonnes])

% Top Emitters Without P2 Plan =
DIVIDE(
    CALCULATE(COUNTROWS(vw_p2_gap_analysis),
        vw_p2_gap_analysis[emitter_tier] = "Top emitter (100kt+)",
        vw_p2_gap_analysis[has_p2_plan] = 0),
    CALCULATE(COUNTROWS(vw_p2_gap_analysis),
        vw_p2_gap_analysis[emitter_tier] = "Top emitter (100kt+)")
)

Avg 3yr Emissions Trend = AVERAGE(vw_p2_gap_analysis[three_year_emissions_trend_pct])
```

## Suggested pages

1. **National overview** — KPI cards (Total Facilities, Total CO2e,
   % Top Emitters Without P2 Plan), a map of `vw_province_summary`
   (bubble size = total_co2e_tonnes, color = pct_with_p2_plan), and a
   trend line from `vw_emissions_trend_by_gas`.
2. **Sector view** — bar chart of `vw_sector_summary` sorted by
   total_co2e_tonnes, with a secondary axis or color encoding for
   pct_with_p2_plan — this is the chart that carries the headline
   finding.
3. **Facility drill-down** — table from `vw_p2_gap_analysis`, filterable
   by province/sector/emitter_tier, sortable by
   three_year_emissions_trend_pct so a viewer can find both the worst
   performers and the ones genuinely improving.
4. **Slicers** — province, NAICS sector, emitter tier, has_p2_plan.

## A note on framing the "impact"

Resist the urge to editorialize about specific named facilities/
companies in the write-up beyond what the public data says — stick to
descriptive statistics (counts, percentages, trends) rather than
implying wrongdoing. The dataset's own purpose (as ECCC states) is
transparency and informing pollution-prevention priorities, so framing
your dashboard the same way — "here's where the biggest gaps are" — is
both more defensible and closer to what an actual sustainability
consulting deliverable looks like than a "gotcha" framing would be.
