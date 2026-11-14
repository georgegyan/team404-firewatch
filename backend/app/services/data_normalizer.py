
from pathlib import Path

import pandas as pd


# Common columns used by the FireWatch application.
STANDARD_COLUMNS = [
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "acq_datetime_utc",
    "satellite",
    "sensor",
    "instrument",
    "confidence_raw",
    "confidence_type",
    "frp",
    "brightness_primary",
    "brightness_primary_field",
    "brightness_secondary",
    "brightness_secondary_field",
    "daynight",
    "source_file",
]


SENSOR_CONFIG = {
    "modis": {
        "sensor": "MODIS",
        "primary_brightness": "brightness",
        "secondary_brightness": "bright_t31",
        "confidence_type": "numeric_0_100",
    },
    "viirs_noaa20": {
        "sensor": "VIIRS_NOAA20",
        "primary_brightness": "bright_ti4",
        "secondary_brightness": "bright_ti5",
        "confidence_type": "categorical",
    },
    "viirs_noaa21": {
        "sensor": "VIIRS_NOAA21",
        "primary_brightness": "bright_ti4",
        "secondary_brightness": "bright_ti5",
        "confidence_type": "categorical",
    },
    "viirs_snpp": {
        "sensor": "VIIRS_SNPP",
        "primary_brightness": "bright_ti4",
        "secondary_brightness": "bright_ti5",
        "confidence_type": "categorical",
    },
}


def get_sensor_config(file_path: Path):
    """Identify the sensor from the raw filename."""

    filename = file_path.name.lower()

    for prefix, config in SENSOR_CONFIG.items():
        if filename.startswith(prefix):
            return config

    raise ValueError(
        f"Cannot identify sensor from filename: {file_path.name}"
    )


def create_acquisition_datetime(df: pd.DataFrame):
    """Convert FIRMS acquisition date and HHMM time to UTC."""

    date = df["acq_date"].astype("string").str.strip()

    time = (
        df["acq_time"]
        .astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .str.zfill(4)
    )

    valid_time = time.str.match(r"^\d{4}$", na=False)

    time = time.where(valid_time)

    return pd.to_datetime(
        date + " " + time,
        format="%Y-%m-%d %H%M",
        errors="coerce",
        utc=True,
    )


def normalize_firms_file(file_path: Path):
    """Normalize one original FIRMS CSV without changing its raw file."""

    df = pd.read_csv(file_path)

    config = get_sensor_config(file_path)

    required_columns = [
        "latitude",
        "longitude",
        "acq_date",
        "acq_time",
        "confidence",
        "frp",
    ]

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{file_path.name} is missing columns: {missing}"
        )

    normalized = pd.DataFrame(index=df.index)

    normalized["latitude"] = pd.to_numeric(
        df["latitude"], errors="coerce"
    )

    normalized["longitude"] = pd.to_numeric(
        df["longitude"], errors="coerce"
    )

    normalized["acq_date"] = df["acq_date"].astype("string")

    normalized["acq_time"] = (
        df["acq_time"]
        .astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(4)
    )

    normalized["acq_datetime_utc"] = (
        create_acquisition_datetime(df)
    )

    normalized["satellite"] = (
        df["satellite"].astype("string")
        if "satellite" in df.columns
        else pd.NA
    )

    normalized["sensor"] = config["sensor"]

    normalized["instrument"] = (
        df["instrument"].astype("string")
        if "instrument" in df.columns
        else pd.NA
    )

    # Preserve the original confidence value and its scale.
    # MODIS numeric confidence is not equivalent to VIIRS
    # categorical confidence.
    normalized["confidence_raw"] = (
        df["confidence"].astype("string")
    )

    normalized["confidence_type"] = config["confidence_type"]

    normalized["frp"] = pd.to_numeric(
        df["frp"], errors="coerce"
    )

    primary = config["primary_brightness"]
    secondary = config["secondary_brightness"]

    normalized["brightness_primary"] = (
        pd.to_numeric(df[primary], errors="coerce")
        if primary in df.columns
        else pd.NA
    )

    normalized["brightness_primary_field"] = primary

    normalized["brightness_secondary"] = (
        pd.to_numeric(df[secondary], errors="coerce")
        if secondary in df.columns
        else pd.NA
    )

    normalized["brightness_secondary_field"] = secondary

    normalized["daynight"] = (
        df["daynight"].astype("string")
        if "daynight" in df.columns
        else pd.NA
    )

    normalized["source_file"] = file_path.name

    # Remove records without usable coordinates.
    normalized = normalized.dropna(
        subset=["latitude", "longitude"]
    )

    # Validate geographic coordinate ranges.
    normalized = normalized[
        normalized["latitude"].between(-90, 90)
        & normalized["longitude"].between(-180, 180)
    ]

    return normalized[STANDARD_COLUMNS]


def normalize_firms_files(file_paths):
    """Normalize multiple FIRMS files into one dataset."""

    datasets = []

    for file_path in file_paths:
        print(f"Processing: {file_path.name}")

        normalized = normalize_firms_file(file_path)

        print(
            f"Normalized {len(normalized)} records "
            f"from {SENSOR_CONFIG[get_sensor_config(file_path)['sensor'].lower()]['sensor']}"
        )

        datasets.append(normalized)

    if not datasets:
        raise ValueError("No FIRMS files were provided.")

    return pd.concat(
        datasets,
        ignore_index=True
    )
