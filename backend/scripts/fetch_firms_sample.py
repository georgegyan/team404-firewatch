
import os
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


# ---------------------------------------------------------
# 1. Project paths and configuration
# ---------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = BACKEND_DIR / "data" / "raw"
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(ENV_FILE)

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

# Approximate Ghana bounding box:
# west, south, east, north
GHANA_BBOX = "-3.3,4.5,1.3,11.2"

# NASA FIRMS Area API
API_BASE_URL = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
)

# We are testing one MODIS source and one VIIRS source.
SOURCES = {
    "MODIS": "MODIS_NRT",
    "VIIRS_SNPP": "VIIRS_SNPP_NRT",
}

DAY_RANGE = 5
TIMEOUT_SECONDS = 60


# ---------------------------------------------------------
# 2. Retrieve records from NASA FIRMS
# ---------------------------------------------------------

def fetch_sensor_data(sensor_name: str, source: str):
    """Fetch recent fire detections for one FIRMS source."""

    url = (
        f"{API_BASE_URL}/"
        f"{MAP_KEY}/"
        f"{source}/"
        f"{GHANA_BBOX}/"
        f"{DAY_RANGE}"
    )

    print(f"\nRequesting {sensor_name} data...")

    try:
        response = requests.get(
            url,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"{sensor_name}: NASA FIRMS request timed out."
        )

    except requests.exceptions.HTTPError:
        raise RuntimeError(
            f"{sensor_name}: NASA FIRMS returned "
            f"HTTP {response.status_code}. "
            "Check your MAP_KEY and API access."
        )

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"{sensor_name}: Network request failed: "
            f"{error.__class__.__name__}"
        )

    # Parse the returned CSV.
    try:
        dataframe = pd.read_csv(StringIO(response.text))

    except (pd.errors.ParserError, pd.errors.EmptyDataError):
        message = response.text[:250].strip()

        raise RuntimeError(
            f"{sensor_name}: The API did not return a valid CSV.\n"
            f"Response preview: {message}"
        )

    # Check that the response contains the fields we need.
    required_columns = {
        "latitude",
        "longitude",
        "acq_date",
    }

    missing_columns = required_columns.difference(
        dataframe.columns
    )

    if missing_columns:
        raise RuntimeError(
            f"{sensor_name}: CSV is missing expected columns: "
            f"{', '.join(sorted(missing_columns))}"
        )

    print(f"Retrieved {len(dataframe):,} records.")

    return dataframe, response.text


# ---------------------------------------------------------
# 3. Save original CSV responses
# ---------------------------------------------------------

def save_raw_data(sensor_name: str, csv_text: str):
    """Save the original NASA CSV response without modification."""

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    filename = (
        f"{sensor_name.lower()}_ghana_nrt_"
        f"last_{DAY_RANGE}_days_{date_stamp}.csv"
    )

    output_path = RAW_DATA_DIR / filename

    output_path.write_text(
        csv_text,
        encoding="utf-8",
    )

    print(f"Saved raw file: {output_path}")

    return output_path


# ---------------------------------------------------------
# 4. Display a simple data report
# ---------------------------------------------------------

def display_report(sensor_name: str, dataframe: pd.DataFrame):
    print(f"\n{'-' * 55}")
    print(f"{sensor_name} DATA REPORT")
    print(f"{'-' * 55}")

    print(f"Total detections: {len(dataframe):,}")

    if dataframe.empty:
        print("No detections were returned for this period.")
        return

    print(
        "Date range: "
        f"{dataframe['acq_date'].min()} to "
        f"{dataframe['acq_date'].max()}"
    )

    print("\nAvailable columns:")
    print(", ".join(dataframe.columns))

    print("\nFirst five records:")

    preview_columns = [
        column
        for column in [
            "latitude",
            "longitude",
            "acq_date",
            "acq_time",
            "satellite",
            "confidence",
            "frp",
        ]
        if column in dataframe.columns
    ]

    print(
        dataframe[preview_columns]
        .head()
        .to_string(index=False)
    )


# ---------------------------------------------------------
# 5. Main program
# ---------------------------------------------------------

def main():
    print("=" * 55)
    print("TERRASIGNAL FIREWATCH")
    print("NASA FIRMS DATA ACQUISITION TEST")
    print("=" * 55)

    if not MAP_KEY:
        raise RuntimeError(
            "FIRMS_MAP_KEY was not found.\n"
            f"Check that your key is saved in: {ENV_FILE}"
        )

    print("MAP_KEY loaded successfully.")
    print(f"Study area: Ghana (approximate bounding box)")
    print(f"Period: Latest {DAY_RANGE} days")
    print("Data type: Near Real-Time (NRT)")

    results = {}

    for sensor_name, source in SOURCES.items():
        dataframe, csv_text = fetch_sensor_data(
            sensor_name,
            source,
        )

        save_raw_data(sensor_name, csv_text)

        display_report(sensor_name, dataframe)

        results[sensor_name] = len(dataframe)

    print("\n" + "=" * 55)
    print("ACQUISITION SUMMARY")
    print("=" * 55)

    for sensor_name, count in results.items():
        print(f"{sensor_name}: {count:,} detections")

    print("\nBoth sensor requests completed successfully.")
    print("Original CSV files are stored in backend/data/raw/")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"\nERROR: {error}")
        raise SystemExit(1)
