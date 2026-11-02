
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "iss" / "iss_propagated_positions.parquet"

EXPECTED_ROWS = 289
EXPECTED_NORAD_ID = 25544
STEP_MINUTES = 5

POSITION_COLUMNS = ["x_km", "y_km", "z_km"]
VELOCITY_COLUMNS = ["vx_km_s", "vy_km_s", "vz_km_s"]


def validate_propagation_data(df):
    required_columns = [
        "timestamp_utc",
        "norad_id",
        *POSITION_COLUMNS,
        *VELOCITY_COLUMNS,
    ]

    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    if len(df) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} rows, found {len(df)}")

    if df["norad_id"].nunique() != 1:
        raise ValueError("Expected exactly one unique NORAD ID")

    if int(df["norad_id"].iloc[0]) != EXPECTED_NORAD_ID:
        raise ValueError("Unexpected satellite NORAD ID")

    if df["timestamp_utc"].isna().any():
        raise ValueError("Missing timestamps found")

    if not df["timestamp_utc"].is_monotonic_increasing:
        raise ValueError("Timestamps are not monotonically increasing")

    if df["timestamp_utc"].duplicated().any():
        raise ValueError("Duplicate timestamps found")

    numeric_columns = POSITION_COLUMNS + VELOCITY_COLUMNS
    values = df[numeric_columns].to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError("Non-finite position or velocity values found")

    position_norm = np.linalg.norm(df[POSITION_COLUMNS].to_numpy(), axis=1)
    velocity_norm = np.linalg.norm(df[VELOCITY_COLUMNS].to_numpy(), axis=1)

    if not np.all((position_norm > 6000) & (position_norm < 50000)):
        raise ValueError("Position magnitude outside the expected broad range")

    if not np.all((velocity_norm > 1) & (velocity_norm < 15)):
        raise ValueError("Velocity magnitude outside the expected broad range")

    intervals = (
        pd.to_datetime(df["timestamp_utc"]).diff().dropna().dt.total_seconds() / 60
    )

    if not np.allclose(intervals, STEP_MINUTES):
        raise ValueError("Unexpected timestamp intervals")

    return {
        "rows": len(df),
        "unique_norad_ids": df["norad_id"].nunique(),
        "position_min_km": position_norm.min(),
        "position_max_km": position_norm.max(),
        "velocity_min_km_s": velocity_norm.min(),
        "velocity_max_km_s": velocity_norm.max(),
    }


def validate_propagation():
    df = pd.read_parquet(INPUT_FILE)
    report = validate_propagation_data(df)

    print("Propagation validation passed.")
    print(f"Rows: {report['rows']}")
    print(f"Unique NORAD IDs: {report['unique_norad_ids']}")
    print(f"Time interval: {STEP_MINUTES} minutes")
    print(
        f"Position magnitude: {report['position_min_km']:.2f}–"
        f"{report['position_max_km']:.2f} km"
    )
    print(
        f"Velocity magnitude: {report['velocity_min_km_s']:.3f}–"
        f"{report['velocity_max_km_s']:.3f} km/s"
    )


if __name__ == "__main__":
    validate_propagation()
