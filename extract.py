import os
import psycopg
from dotenv import load_dotenv
from openelectricity import OEClient
from openelectricity.types import DataMetric
from datetime import datetime, timezone, date, timedelta
import requests
import argparse

load_dotenv()

def get_weather(start_date, end_date):
    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    CITIES = {
    "Perth": {"coordinates": (-31.95, 115.86)},
    "Brisbane": {"coordinates": (-27.47, 153.03),},
    "Melbourne": {"coordinates": (-37.81, 144.96),},
    "Sydney": {"coordinates": (-33.87, 151.21),},
    "Adelaide": {"coordinates": (-34.93, 138.60)},
    "Hobart": {"coordinates": (-42.88, 147.33),},
}
    weather_data = {}
    for city, details in CITIES.items():
        latitude, longitude = details["coordinates"]
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,precipitation,surface_pressure,cloud_cover,wind_speed_10m,is_day",
            "timezone": "UTC",
        }
        response = requests.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        weather_data[city] = {
            "response": response
        }
    return weather_data

def flatten_weather(weather_data):
    
    weather_flattened = []

    for city, details in weather_data.items():
        response = details["response"]

        hourly = response.json()["hourly"]

        for time, temperature, precipitation, surface_pressure, cloud_cover, wind_speed_10m, isday in zip(
            hourly["time"],
            hourly["temperature_2m"],
            hourly["precipitation"],
            hourly["surface_pressure"],
            hourly["cloud_cover"],
            hourly["wind_speed_10m"],
            hourly["is_day"]
        ):
            weather_flattened.append(
                {
                    "timestamp": time,
                    "city": city,
                    "temperature_2m": temperature,
                    "precipitation": precipitation,
                    "surface_pressure": surface_pressure,
                    "cloud_cover": cloud_cover,
                    "wind_speed_10m": wind_speed_10m,
                    "is_day": isday
                }
            )
    return weather_flattened

def load_weather_to_postgres(weather_flattened):
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    if not postgres_password:
        raise RuntimeError(
            "Set POSTGRES_PASSWORD in .env before running this script."
        )

    conn = psycopg.connect(
            dbname="test",
            user="postgres",
            password=postgres_password,
            host="localhost"
        )

    cur = conn.cursor()

    cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_weather (
                timestamp TIMESTAMPTZ,
                city TEXT,
                temperature_2m NUMERIC(12,6),
                precipitation NUMERIC(12,6),
                surface_pressure NUMERIC(12,6),
                cloud_cover NUMERIC(12,6),
                wind_speed_10m NUMERIC(12,6),
                is_day BOOLEAN,
                    
                PRIMARY KEY (
                    timestamp,
                    city
                )
            );
        """)
    
    for row in weather_flattened:
        timestamp = datetime.fromisoformat(row["timestamp"])
        timestamp = timestamp.replace(tzinfo=timezone.utc)
        cur.execute(
            """
            INSERT INTO raw_weather (
            timestamp,
            city,
            temperature_2m,
            precipitation,
            surface_pressure,
            cloud_cover,
            wind_speed_10m,     
            is_day
            )

            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (
                timestamp,
                city
            )
            DO UPDATE SET
                temperature_2m = EXCLUDED.temperature_2m,
                precipitation = EXCLUDED.precipitation,
                surface_pressure = EXCLUDED.surface_pressure,
                cloud_cover = EXCLUDED.cloud_cover,
                wind_speed_10m  = EXCLUDED.wind_speed_10m,
                is_day = EXCLUDED.is_day

            """,
            (
                timestamp,
                row["city"],
                row["temperature_2m"],
                row["precipitation"],
                row["surface_pressure"],
                row["cloud_cover"],
                row["wind_speed_10m"],
                bool(row["is_day"])
             )
        )

    conn.commit()
    cur.close()
    conn.close()

def get_electricity(start_date, end_date):
    start_datetime = datetime.fromisoformat(start_date)
    end_datetime = datetime.fromisoformat(end_date)

    api_key = os.getenv("OPEN_ELECTRICITY_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Set OPEN_ELECTRICITY_API_KEY in .env before running this script."
        )

    with OEClient(api_key=api_key) as client:
        nem_response = client.get_network_data(
            network_code="NEM",
            metrics=[DataMetric.POWER],
            interval="1h",
            date_start=start_datetime,
            date_end=end_datetime,
            primary_grouping="network_region",
            secondary_grouping="fueltech_group",
        )

        wem_response = client.get_network_data(
            network_code="WEM",
            metrics=[DataMetric.POWER],
            interval="1h",
            date_start=start_datetime,
            date_end=end_datetime,
            primary_grouping="network_region",
            secondary_grouping="fueltech_group",
        )

    return {
        "NEM": nem_response,
        "WEM": wem_response,
    }

def flatten_electricity(electricity_data):
    electricity_flattened = []

    for network_code, response in electricity_data.items():
        for network_series in response.data:
            for result in network_series.results:
                for data_point in result.data:
                    timestamp, power = data_point.root

                    region = result.name.split("_")[1].split("|")[0]

                    row = {
                        "network_code": network_code,
                        "network_region": region,
                        "fueltech_group": result.columns.fueltech_group,
                        "timestamp": timestamp,
                        "power": power,
                    }

                    electricity_flattened.append(row)

    return electricity_flattened

def load_electricity_to_postgres(electricity_flattened):
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    if not postgres_password:
        raise RuntimeError(
            "Set POSTGRES_PASSWORD in .env before running this script."
        )

    conn = psycopg.connect(
        dbname="test",
        user="postgres",
        password=postgres_password,
        host="localhost"
    )

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw_electricity (
            network_code TEXT,
            network_region TEXT,
            fueltech_group TEXT,
            timestamp TIMESTAMPTZ,
            power NUMERIC(12,6),

            PRIMARY KEY (
                network_code,
                network_region,
                fueltech_group,
                timestamp
            )
        );
    """)

    for row in electricity_flattened:
        cur.execute(
            """
            INSERT INTO raw_electricity (
                network_code,
                network_region,
                fueltech_group,
                timestamp,
                power
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (
                network_code,
                network_region,
                fueltech_group,
                timestamp
            )
            DO UPDATE SET
                power = EXCLUDED.power;
            """,
            (
                row["network_code"],
                row["network_region"],
                row["fueltech_group"],
                row["timestamp"],
                row["power"]
            )
        )

    conn.commit()
    cur.close()
    conn.close()

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--start-date", type=str)
    parser.add_argument("--end-date", type=str)

    args = parser.parse_args()

    today = date.today()

    start_date = args.start_date or str(today - timedelta(days=7))
    end_date = args.end_date or str(today - timedelta(days=1))

    print(f"Extracting {start_date} to {end_date}")

    electricity_data = get_electricity(
        start_date,
        end_date
    )

    electricity_flattened = flatten_electricity(electricity_data)
    load_electricity_to_postgres(electricity_flattened)

    weather_data = get_weather(
        start_date,
        end_date
    )

    weather_flattened = flatten_weather(weather_data)
    load_weather_to_postgres(weather_flattened)


if __name__ == "__main__":
    main()