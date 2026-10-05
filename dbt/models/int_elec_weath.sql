SELECT
    e.timestamp,
    e.network_code,
    e.network_region,
    e.fueltech_group,
    e.power_mw,
    w.city,
    w.temperature_c,
    w.precipitation_mm,
    w.surface_pressure_hpa,
    w.cloud_cover_pct,
    w.wind_speed_10m_kmph,
    w.is_day
FROM {{ ref('stg_weather') }} AS w
INNER JOIN {{ ref('stg_electricity') }} AS e
    ON w.timestamp = e.timestamp
    AND w.network_region = e.network_region