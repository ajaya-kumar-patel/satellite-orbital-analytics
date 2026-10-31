import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sgp4 import omm
from sgp4.api import Satrec, WGS72, jday


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ISS_SNAPSHOT = PROJECT_ROOT / "data/raw/iss/iss_gp_snapshot.json"
CANDIDATE_CATALOG = (PROJECT_ROOT / "data/processed/iss/clean_candidate_satellites.json")

REFINED_FILE = (PROJECT_ROOT / "data/processed/iss/close_approach_refined.parquet")

TARGET_NORAD_ID = 48380  # STARLINK-2614
WINDOW_SECONDS = 60      # +/- 60 seconds around the existing estimated TCA

TIME_STEPS_SECONDS = [10, 5, 1, 0.1]


def initialize_satellite(record):
    satellite = Satrec()
    omm.initialize(satellite, record, WGS72)
    return satellite


def propagate_at(satellite, timestamp):
    jd, fraction = jday(
        timestamp.year,
        timestamp.month,
        timestamp.day,
        timestamp.hour,
        timestamp.minute,
        timestamp.second + timestamp.microsecond / 1_000_000,
    )

    error_code, position, velocity = satellite.sgp4(jd, fraction)

    if error_code != 0:
        return None

    position = np.asarray(position, dtype=float)
    velocity = np.asarray(velocity, dtype=float)

    if not np.all(np.isfinite(position)):
        return None

    if not np.all(np.isfinite(velocity)):
        return None

    return position, velocity


def main():
    for path in (ISS_SNAPSHOT, CANDIDATE_CATALOG, REFINED_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    with ISS_SNAPSHOT.open("r", encoding="utf-8") as file:
        iss_data = json.load(file)

    with CANDIDATE_CATALOG.open("r", encoding="utf-8") as file:
        catalog_data = json.load(file)

    refined = pd.read_parquet(REFINED_FILE)

    target_rows = refined.loc[refined["norad_id"] == TARGET_NORAD_ID]

    if len(target_rows) != 1:
        raise ValueError(
            f"Expected one refined row for NORAD {TARGET_NORAD_ID}; "
            f"found {len(target_rows)}"
        )

    target = target_rows.iloc[0]
    center = pd.to_datetime(
        target["refined_tca_estimate_utc"], utc=True
    ).to_pydatetime()

    iss_record = iss_data["orbital_data"]

    candidate_records = {
        int(record["NORAD_CAT_ID"]): record
        for record in catalog_data["orbital_data"]
    }

    candidate_record = candidate_records.get(TARGET_NORAD_ID)

    if candidate_record is None:
        raise ValueError(
            f"NORAD {TARGET_NORAD_ID} not found in candidate catalog"
        )

    iss_satellite = initialize_satellite(iss_record)
    candidate_satellite = initialize_satellite(candidate_record)

    print(f"Target: {target['object_name']} ({TARGET_NORAD_ID})")
    print(f"Center TCA estimate: {center.isoformat()}")
    print(f"Search window: +/- {WINDOW_SECONDS} seconds")
    print(f"Previous 10-second minimum: "
          f"{target['refined_min_distance_km']:.6f} km")

    results = []

    for step_seconds in TIME_STEPS_SECONDS:
        best = None
        valid_samples = 0

        offsets = np.arange(
            -WINDOW_SECONDS,
            WINDOW_SECONDS + step_seconds / 2,
            step_seconds,
        )

        for offset in offsets:
            offset = round(float(offset), 6)

            timestamp = center + timedelta(seconds=offset)

            iss_state = propagate_at(iss_satellite, timestamp)
            candidate_state = propagate_at(candidate_satellite, timestamp)

            if iss_state is None or candidate_state is None:
                continue

            iss_position, _ = iss_state
            candidate_position, _ = candidate_state

            distance_km = float(
                np.linalg.norm(candidate_position - iss_position)
            )
            valid_samples += 1

            if best is None or distance_km < best["distance_km"]:
                best = {
                    "timestamp": timestamp,
                    "distance_km": distance_km,
                    "offset_seconds": offset,
                }

        if best is None:
            raise RuntimeError(
                f"No valid samples for time step {step_seconds} seconds"
            )

        results.append({
            "time_step_seconds": step_seconds,
            "tca_estimate_utc": best["timestamp"],
            "offset_from_original_tca_seconds": best["offset_seconds"],
            "minimum_separation_km": best["distance_km"],
            "valid_samples": valid_samples,
            "boundary_minimum": abs(best["offset_seconds"]) == WINDOW_SECONDS,
        })

    results_df = pd.DataFrame(results)

    baseline = results_df.loc[
        results_df["time_step_seconds"] == 10,
        "minimum_separation_km",
    ].iloc[0]

    results_df["difference_from_10s_km"] = (
        results_df["minimum_separation_km"] - baseline
    )

    print("\nTIME-RESOLUTION COMPARISON")
    print(
        results_df.to_string(
            index=False,
            formatters={
                "minimum_separation_km": "{:.9f}".format,
                "difference_from_10s_km": "{:+.9f}".format,
            },
        )
    )

    if results_df["boundary_minimum"].any():
        print(
            "\nWARNING: At least one minimum lies at the edge of the "
            "comparison window. A wider window may be needed."
        )

    output_file = (
        PROJECT_ROOT
        / "data/processed/iss/tca_time_resolution_check.parquet"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_parquet(output_file, index=False)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
