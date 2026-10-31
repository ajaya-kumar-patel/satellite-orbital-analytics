from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (PROJECT_ROOT / "data" / "processed" / "iss" / "iss_propagated_positions.parquet")

EXPECTED_ROWS = 289
EXPECTED_NORAD_ID = 25544
STEP_MINUTES = 5

POSITION_COLUMNS = ["x_km", "y_km", "z_km"]
VELOCITY_COLUMNS = ["vx_km_s", "vy_km_s", "vz_km_s"]


def validate_propagation():
    df = pd.read_parquet(INPUT_FILE)

    required_columns = ["timestamp_utc", "norad_id", *POSITION_COLUMNS, *VELOCITY_COLUMNS,]

    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    assert len(df) == EXPECTED_ROWS, (f"Expected {EXPECTED_ROWS} rows, found {len(df)}")

    assert df["norad_id"].nunique() == 1
    assert int(df["norad_id"].iloc[0]) == EXPECTED_NORAD_ID

    assert df["timestamp_utc"].is_monotonic_increasing
    assert not df["timestamp_utc"].duplicated().any()

    numeric_columns = POSITION_COLUMNS + VELOCITY_COLUMNS

    assert np.isfinite(df[numeric_columns].to_numpy()).all(), ("Non-finite position or velocity values found")

    position_norm = np.linalg.norm(df[POSITION_COLUMNS].to_numpy(), axis=1)

    velocity_norm = np.linalg.norm(df[VELOCITY_COLUMNS].to_numpy(), axis=1)

    # Basic plausibility checks for an Earth-orbiting satellite.
    assert np.all((position_norm > 6_000) & (position_norm < 50_000)), ("Position magnitude outside the expected broad range")

    assert np.all((velocity_norm > 1) & (velocity_norm < 15)), ("Velocity magnitude outside the expected broad range")

    intervals = (pd.to_datetime(df["timestamp_utc"]).diff().dropna().dt.total_seconds() / 60)

    assert np.allclose(intervals, STEP_MINUTES), ("Unexpected timestamp intervals")

    print("Propagation validation passed.")
    print(f"Rows: {len(df)}")
    print(f"Unique NORAD IDs: {df['norad_id'].nunique()}")
    print(f"Time interval: {STEP_MINUTES} minutes")
    print(f"Position magnitude: {position_norm.min():.2f}–"
          f"{position_norm.max():.2f} km")
    print(f"Velocity magnitude: {velocity_norm.min():.3f}–"
          f"{velocity_norm.max():.3f} km/s")
    print(f"Missing values: {int(df[required_columns].isna().sum().sum())}")


if __name__ == "__main__":
    validate_propagation()
