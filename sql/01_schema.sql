/* ============================================================
   Canadian Industrial Emissions — Azure SQL Database schema
   Built around the real structure of ECCC's GHGRP data files.
   ============================================================ */

IF OBJECT_ID('dbo.fact_emissions_by_gas', 'U') IS NOT NULL DROP TABLE dbo.fact_emissions_by_gas;
IF OBJECT_ID('dbo.fact_emissions_by_source', 'U') IS NOT NULL DROP TABLE dbo.fact_emissions_by_source;
IF OBJECT_ID('dbo.fact_facility_enriched', 'U') IS NOT NULL DROP TABLE dbo.fact_facility_enriched;
IF OBJECT_ID('dbo.dim_facility', 'U') IS NOT NULL DROP TABLE dbo.dim_facility;

CREATE TABLE dbo.dim_facility (
    facility_id         INT             NOT NULL PRIMARY KEY,
    facility_name        NVARCHAR(300)   NOT NULL,
    ghgrp_id                NVARCHAR(50)    NULL,
    npri_id                  BIGINT          NULL,
    province                   NVARCHAR(50)    NULL,
    naics_code                  NVARCHAR(20)    NULL,
    naics_description            NVARCHAR(300)   NULL
);

CREATE TABLE dbo.fact_emissions_by_gas (
    row_id              INT IDENTITY(1,1) PRIMARY KEY,
    facility_id           INT             NOT NULL,
    year                    SMALLINT        NOT NULL,
    gas_type                 NVARCHAR(20)    NOT NULL,
    quantity_tonnes            DECIMAL(18, 2)  NULL,
    quantity_co2e_tonnes         DECIMAL(18, 2)  NULL,

    CONSTRAINT FK_gas_facility FOREIGN KEY (facility_id) REFERENCES dbo.dim_facility (facility_id)
);

CREATE TABLE dbo.fact_emissions_by_source (
    row_id              INT IDENTITY(1,1) PRIMARY KEY,
    facility_id           INT             NOT NULL,
    year                    SMALLINT        NOT NULL,
    source_category           NVARCHAR(100)   NOT NULL,
    quantity_co2e_tonnes         DECIMAL(18, 2)  NULL,

    CONSTRAINT FK_source_facility FOREIGN KEY (facility_id) REFERENCES dbo.dim_facility (facility_id)
);

CREATE INDEX IX_gas_facility_year    ON dbo.fact_emissions_by_gas (facility_id, year);
CREATE INDEX IX_source_facility_year ON dbo.fact_emissions_by_source (facility_id, year);

/* ============================================================
   Reconciled table — populated by
   etl/reconcile_and_transform.py after joining in the MongoDB
   P2 activity data. This is the headline analytical table:
   each facility's total emissions alongside what it's actually
   doing about pollution prevention.
   ============================================================ */
CREATE TABLE dbo.fact_facility_enriched (
    facility_id                 INT             NOT NULL PRIMARY KEY,
    facility_name                 NVARCHAR(300)   NOT NULL,
    province                        NVARCHAR(50)    NULL,
    naics_description                 NVARCHAR(300)   NULL,
    latest_year                         SMALLINT        NULL,
    latest_year_co2e_tonnes               DECIMAL(18, 2)  NULL,
    three_year_emissions_trend_pct           DECIMAL(10, 2)  NULL,  -- % change over 3 years; can be extreme when the
                                                                     -- base year was a near-zero anomaly (shutdown,
                                                                     -- reporting gap) rather than typical operation --
                                                                     -- see trend_baseline_flag
    trend_baseline_flag                        NVARCHAR(20)    NULL,  -- 'low_base' when the 3-yr-prior baseline is
                                                                       -- under 1% of the facility's own max reported
                                                                       -- year, i.e. the trend pct is likely an
                                                                       -- artifact rather than a real growth signal
    has_p2_plan                                BIT             NOT NULL DEFAULT 0,     -- from MongoDB (NPRI)
    has_p2_activity                              BIT             NOT NULL DEFAULT 0,     -- from MongoDB (NPRI)
    load_timestamp                                 DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_enriched_facility FOREIGN KEY (facility_id) REFERENCES dbo.dim_facility (facility_id)
);
