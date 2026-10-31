from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ISS_FILE = (PROJECT_ROOT / "data" / "processed" / "iss" / "iss_propagated_positions.parquet")

CANDIDATES_FILE = (PROJECT_ROOT / "data" / "processed" / "iss" / "candidate_propagated_positions.parquet")

OUTPUT_FILE = (PROJECT_ROOT / "data" / "processed" / "iss" / "close_approach_screening.parquet")

# Broad screening threshold, not a collision-probability threshold.
SCREENING_DISTANCE_KM = 100.0

POSITION_COLUMNS = ["x_km", "y_km", "z_km"]


def main():
    print("Loading ISS positions...")
    iss = pd.read_parquet(ISS_FILE)

    print("Loading candidate positions...")
    candidates = pd.read_parquet(CANDIDATES_FILE)

    # Match positions only at the same timestamps.
    merged = candidates.merge(
        iss[["timestamp_utc", *POSITION_COLUMNS]],
        on="timestamp_utc",
        how="inner",
        suffixes=("_candidate", "_iss"),
        validate="many_to_one",
    )

    print(f"Matched position records: {len(merged)}")

    candidate_xyz = merged[["x_km_candidate", "y_km_candidate", "z_km_candidate"]].to_numpy()

    iss_xyz = merged[["x_km_iss", "y_km_iss", "z_km_iss"]].to_numpy()

    merged["distance_km"] = np.linalg.norm(candidate_xyz - iss_xyz, axis=1)

    close = merged.loc[
        merged["distance_km"] <= SCREENING_DISTANCE_KM,
        ["timestamp_utc", "norad_id", "object_name", "distance_km"],
    ].copy()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    close.to_parquet(OUTPUT_FILE, index=False)

    print("\nClose-approach screening completed.")
    print(f"Screening threshold: {SCREENING_DISTANCE_KM} km")
    print(f"Records within threshold: {len(close)}")
    print(f"Unique candidate satellites: {close['norad_id'].nunique()}")

    if not close.empty:
        print("\nTen closest timestamp-matched positions:")
        print(close.sort_values("distance_km").head(10).to_string(index=False))
        print("\nOutput file:")
        print(OUTPUT_FILE)
    else:
        print("No timestamp-matched positions fell within the threshold.")
        print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
