{{ config(materialized='table') }}

SELECT
    timestamp,
    network_code,
    network_region,
    fueltech_group,
    power_mw,
    city,
    temperature_c,
    precipitation_mm,
    surface_pressure_hpa,
    cloud_cover_pct,
    wind_speed_10m_kmph,
    is_day
FROM {{ ref('int_elec_weath') }}
ORDER BY timestamp, network_code, network_region, fueltech_group