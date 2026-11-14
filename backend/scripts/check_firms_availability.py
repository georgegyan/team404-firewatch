
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# Load backend/.env
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    raise ValueError(
        "FIRMS_MAP_KEY was not found in backend/.env"
    )

url = (
    "https://firms.modaps.eosdis.nasa.gov"
    f"/api/data_availability/csv/{MAP_KEY}/all"
)

print("=" * 60)
print("TERRASIGNAL FIREWATCH")
print("NASA FIRMS SENSOR AVAILABILITY CHECK")
print("=" * 60)

response = requests.get(url, timeout=60)
response.raise_for_status()

from io import StringIO

df = pd.read_csv(StringIO(response.text))

print("\nAvailable FIRMS datasets:\n")

if "data_id" not in df.columns:
    print(response.text[:1000])
    raise RuntimeError("Unexpected response from NASA FIRMS.")

print(df.to_string(index=False))

print("\nRelevant sensors:\n")

sensors = [
    "MODIS_NRT",
    "MODIS_SP",
    "VIIRS_SNPP_NRT",
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA20_SP",
    "VIIRS_NOAA21_NRT",
    "VIIRS_NOAA21_SP",
]

for sensor in sensors:
    match = df[df["data_id"] == sensor]

    if not match.empty:
        row = match.iloc[0]
        print(
            f"{sensor}: "
            f"{row['min_date']} to {row['max_date']}"
        )
    else:
        print(f"{sensor}: Not listed")

print("\nAvailability check completed.")
