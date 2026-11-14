
import os
from io import StringIO
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BACKEND_DIR / ".env")

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    raise ValueError(
        "FIRMS_MAP_KEY not found in backend/.env"
    )

BASE_URL = (
    "https://firms.modaps.eosdis.nasa.gov"
    "/api/area/csv"
)

# Approximate Ghana bounding box:
# west, south, east, north
AREA = "-3.3,4.5,1.3,11.2"

DAY_RANGE = 5

RAW_DIR = BACKEND_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DATE_SUFFIX = datetime.now(
    timezone.utc
).strftime("%Y%m%d")


# --------------------------------------------------
# SENSOR CONFIGURATION
# --------------------------------------------------

SENSORS = {
    "MODIS_NRT": "modis_ghana_nrt",
    "VIIRS_NOAA20_NRT": "viirs_noaa20_ghana_nrt",
    "VIIRS_NOAA21_NRT": "viirs_noaa21_ghana_nrt",
}


# --------------------------------------------------
# DATA ACQUISITION
# --------------------------------------------------

def fetch_sensor_data(source):
    """Download the latest FIRMS records for one sensor."""

    url = (
        f"{BASE_URL}/{MAP_KEY}/"
        f"{source}/{AREA}/{DAY_RANGE}"
    )

    response = requests.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    if not response.text.strip():
        raise ValueError(
            f"{source} returned an empty response."
        )

    df = pd.read_csv(StringIO(response.text))

    required_columns = {
        "latitude",
        "longitude",
        "acq_date",
    }

    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"Unexpected response from {source}. "
            f"Returned columns: {list(df.columns)}"
        )

    filename = (
        f"{SENSORS[source]}_"
        f"last_{DAY_RANGE}_days_"
        f"{DATE_SUFFIX}.csv"
    )

    output_path = RAW_DIR / filename

    # Preserve the original CSV response.
    output_path.write_text(
        response.text,
        encoding="utf-8"
    )

    return df, output_path


# --------------------------------------------------
# REPORTING
# --------------------------------------------------

def display_report(source, df, output_path):

    print("\n" + "-" * 55)
    print(f"{source} DATA REPORT")
    print("-" * 55)

    print(f"Total detections: {len(df)}")

    print(f"Saved raw file: {output_path}")

    if df.empty:
        print("No detections returned for this period.")
        return

    dates = pd.to_datetime(
        df["acq_date"],
        errors="coerce"
    ).dropna()

    if not dates.empty:
        print(
            f"Date range: "
            f"{dates.min().date()} to "
            f"{dates.max().date()}"
        )

    print("\nAvailable columns:")
    print(", ".join(df.columns))

    preview_columns = [
        col for col in [
            "latitude",
            "longitude",
            "acq_date",
            "acq_time",
            "satellite",
            "confidence",
            "frp",
        ]
        if col in df.columns
    ]

    print("\nFirst five records:")
    print(
        df[preview_columns]
        .head()
        .to_string(index=False)
    )


# --------------------------------------------------
# MAIN PROGRAM
# --------------------------------------------------

def main():

    print("=" * 55)
    print("TERRASIGNAL FIREWATCH")
    print("NASA FIRMS DATA ACQUISITION")
    print("=" * 55)

    print("MAP_KEY loaded successfully.")
    print("Study area: Ghana (approximate bounding box)")
    print(f"Period: Latest {DAY_RANGE} days")
    print("Data type: Near Real-Time (NRT)")

    results = {}

    for source in SENSORS:

        print(f"\nRequesting {source} data...")

        try:
            df, output_path = fetch_sensor_data(source)

            results[source] = len(df)

            print(f"Retrieved {len(df)} records.")

            display_report(
                source,
                df,
                output_path
            )

        except requests.RequestException as error:
            print(f"Network/API error for {source}: {error}")
            results[source] = None

        except Exception as error:
            print(f"Error processing {source}: {error}")
            results[source] = None

    print("\n" + "=" * 55)
    print("ACQUISITION SUMMARY")
    print("=" * 55)

    for source, count in results.items():

        if count is None:
            print(f"{source}: FAILED")
        else:
            print(f"{source}: {count} detections")

    print("\nSuomi-NPP note:")
    print(
        "Its latest available NRT date was "
        "2 November 2026, so it is excluded "
        "from this latest-five-day test."
    )

    print("\nOriginal CSV files are stored in:")
    print(RAW_DIR)

    print("\nAcquisition test completed.")


if __name__ == "__main__":
    main()
