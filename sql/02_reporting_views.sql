/* ============================================================
   Reporting views — the "so what" layer that Power BI and SSRS
   both read from.
   ============================================================ */

-- The headline finding: high emitters with no pollution prevention plan
CREATE OR ALTER VIEW dbo.vw_p2_gap_analysis AS
SELECT
    facility_id,
    facility_name,
    province,
    naics_description,
    latest_year,
    latest_year_co2e_tonnes,
    three_year_emissions_trend_pct,
    trend_baseline_flag,
    has_p2_plan,
    has_p2_activity,
    CASE
        WHEN latest_year_co2e_tonnes >= 100000 THEN 'Top emitter (100kt+)'
        WHEN latest_year_co2e_tonnes >= 25000  THEN 'Large emitter (25-100kt)'
        ELSE 'Reporting threshold (10-25kt)'
    END AS emitter_tier
FROM dbo.fact_facility_enriched;
GO

-- Sector-level rollup: total emissions and P2 adoption by NAICS description
CREATE OR ALTER VIEW dbo.vw_sector_summary AS
SELECT
    naics_description,
    COUNT(*) AS facility_count,
    SUM(latest_year_co2e_tonnes) AS total_co2e_tonnes,
    AVG(latest_year_co2e_tonnes) AS avg_co2e_tonnes,
    SUM(CASE WHEN has_p2_plan = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS pct_with_p2_plan,
    AVG(three_year_emissions_trend_pct) AS avg_3yr_trend_pct
FROM dbo.fact_facility_enriched
GROUP BY naics_description;
GO

-- Province-level rollup for the map visual
CREATE OR ALTER VIEW dbo.vw_province_summary AS
SELECT
    province,
    COUNT(*) AS facility_count,
    SUM(latest_year_co2e_tonnes) AS total_co2e_tonnes,
    SUM(CASE WHEN has_p2_plan = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS pct_with_p2_plan
FROM dbo.fact_facility_enriched
GROUP BY province;
GO

-- Year-over-year trend by gas type, across all facilities
CREATE OR ALTER VIEW dbo.vw_emissions_trend_by_gas AS
SELECT
    year,
    gas_type,
    SUM(quantity_co2e_tonnes) AS total_co2e_tonnes,
    COUNT(DISTINCT facility_id) AS reporting_facility_count
FROM dbo.fact_emissions_by_gas
GROUP BY year, gas_type;
GO
