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
