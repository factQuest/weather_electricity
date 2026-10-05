select
    network_code,
    network_region,
    fueltech_group,
    timestamp,
    power as power_mw
from {{ source('raw', 'raw_electricity')}}
