
import sys
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Make the backend app package importable.
sys.path.insert(0, str(BACKEND_DIR))

from app.services.data_normalizer import normalize_firms_files


RAW_DIR = BACKEND_DIR / "data" / "raw"
PROCESSED_DIR = BACKEND_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def main():

    print("=" * 60)
    print("TERRASIGNAL FIREWATCH")
    print("FIRMS DATA NORMALIZATION")
    print("=" * 60)

    raw_files = sorted(
        RAW_DIR.glob("*_ghana_nrt_last_5_days_*.csv")
    )

    if not raw_files:
        raise FileNotFoundError(
            "No matching raw NRT files were found. "
            "Run fetch_firms_sample.py first."
        )

    print(f"\nFound {len(raw_files)} raw files.")

    normalized = normalize_firms_files(raw_files)

    output_file = (
        PROCESSED_DIR
        / "ghana_firms_normalized_nrt.csv"
    )

    normalized.to_csv(output_file, index=False)

    print("\n" + "=" * 60)
    print("NORMALIZATION SUMMARY")
    print("=" * 60)

    print(f"Total normalized detections: {len(normalized)}")

    print("\nDetections by sensor:")
    print(normalized["sensor"].value_counts().to_string())

    print("\nRecords by acquisition date:")
    print(
        normalized.groupby("acq_date")
        .size()
        .to_string()
    )

    print("\nStandardized columns:")
    print(", ".join(normalized.columns))

    print("\nFirst five normalized records:")
    print(normalized.head(5).to_string(index=False))

    print(f"\nSaved processed dataset: {output_file}")

    print("\nNormalization completed successfully.")


if __name__ == "__main__":
    main()
