select
    timestamp,
    city,

    case
        when city = 'Perth' then 'WEM'
        when city = 'Brisbane' then 'QLD1'
        when city = 'Sydney' then 'NSW1'
        when city = 'Melbourne' then 'VIC1'
        when city = 'Adelaide' then 'SA1'
        when city = 'Hobart' then 'TAS1'
    end as network_region,

    temperature_2m as temperature_c,
    precipitation as precipitation_mm,
    surface_pressure as surface_pressure_hpa,
    cloud_cover as cloud_cover_pct,
    wind_speed_10m as wind_speed_10m_kmph,
    is_day

from {{ source('raw', 'raw_weather') }}