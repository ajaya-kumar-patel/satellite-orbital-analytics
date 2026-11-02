import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sgp4 import omm
from sgp4.api import Satrec, WGS72, jday


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ISS_SNAPSHOT = (PROJECT_ROOT / "data/raw/iss/iss_gp_snapshot.json")

CANDIDATE_CATALOG = (PROJECT_ROOT / "data/processed/iss/clean_candidate_satellites.json")

SCREENING_FILE = (PROJECT_ROOT / "data/processed/iss/close_approach_screening.parquet")

OUTPUT_FILE = (PROJECT_ROOT / "data/processed/iss/close_approach_refined.parquet")

WINDOW_MINUTES = 10
STEP_SECONDS = 10

QUALITY_RANK = {
    "acceptable": 0,
    "stale": 1,
    "very_stale": 2,
    "highly_stale": 3,
}

def initialize_satellite(record):
    """Initialize an SGP4 satellite from an OMM record."""
    satellite = Satrec()
    omm.initialize(satellite, record, WGS72)
    return satellite


def propagate_at(satellite, timestamp):
    """Return TEME position (km) and velocity (km/s)."""
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

    if not np.all(np.isfinite(position)) or not np.all(np.isfinite(velocity)):
        return None

    return position, velocity


def find_minimum_separation(iss_satellite, candidate_satellite, center, window_minutes=WINDOW_MINUTES, step_seconds=STEP_SECONDS):
    """Find the minimum separation between ISS and a candidate within a time window."""

    offsets = range(
        -window_minutes * 60,
        window_minutes * 60 + 1,
        step_seconds,
    )

    best = None
    best_offset_seconds = None
    valid_samples = 0

    for offset in offsets:
        timestamp = center + timedelta(seconds=offset)

        iss_state = propagate_at(iss_satellite, timestamp)
        candidate_state = propagate_at(candidate_satellite, timestamp)

        if iss_state is None or candidate_state is None:
            continue

        iss_position, iss_velocity = iss_state
        candidate_position, candidate_velocity = candidate_state

        distance_km = float(
            np.linalg.norm(candidate_position - iss_position)
        )

        relative_speed_km_s = float(
            np.linalg.norm(candidate_velocity - iss_velocity)
        )

        valid_samples += 1

        if best is None or distance_km < best["distance_km"]:
            best = {
                "timestamp": timestamp,
                "distance_km": distance_km,
                "relative_speed_km_s": relative_speed_km_s,
            }
            best_offset_seconds = offset

    if best is None:
        return None

    return {
        **best,
        "valid_samples": valid_samples,
        "best_offset_seconds": best_offset_seconds,
        "refinement_boundary_minimum": (
            abs(best_offset_seconds) == window_minutes * 60
        ),
        "refinement_status": (
            "boundary_minimum"
            if abs(best_offset_seconds) == window_minutes * 60
            else "interior_minimum"
        ),
    }


def classify_epoch_quality(offset_hours):
    absolute_offset = abs(offset_hours)

    if absolute_offset <= 24:
        return "acceptable"
    elif absolute_offset <= 48:
        return "stale"
    elif absolute_offset <= 72:
        return "very_stale"
    else:
        return "highly_stale"


def main():
    for path in (ISS_SNAPSHOT, CANDIDATE_CATALOG, SCREENING_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    with ISS_SNAPSHOT.open("r", encoding="utf-8") as file:
        iss_data = json.load(file)

    with CANDIDATE_CATALOG.open("r", encoding="utf-8") as file:
        catalog_data = json.load(file)

    iss_record = iss_data["orbital_data"]
    candidate_records = catalog_data["orbital_data"]

    # Keep the closest 5-minute screening sample for each candidate.
    screening = pd.read_parquet(SCREENING_FILE)

    closest_samples = screening.loc[
        screening.groupby("norad_id")["distance_km"].idxmin()
    ].sort_values("distance_km")


    records_by_id = {
        int(record["NORAD_CAT_ID"]): record
        for record in candidate_records
    }

    iss_satellite = initialize_satellite(iss_record)
    iss_epoch = pd.to_datetime(iss_record["EPOCH"], utc=True)

    offsets = range(
        -WINDOW_MINUTES * 60,
        WINDOW_MINUTES * 60 + 1,
        STEP_SECONDS,
    )

    results = []
    failed = []

    print("Candidates to refine:", len(closest_samples))
    print("Refinement window: +/-", WINDOW_MINUTES, "minutes")
    print("Time step:", STEP_SECONDS, "seconds")

    for _, sample in closest_samples.iterrows():
        norad_id = int(sample["norad_id"])
        object_name = sample["object_name"]

        record = records_by_id.get(norad_id)

        if record is None:
            failed.append((norad_id, "Missing orbital record"))
            continue

        try:
            candidate_satellite = initialize_satellite(record)
            candidate_epoch = pd.to_datetime(record["EPOCH"], utc=True)

            center = pd.to_datetime(sample["timestamp_utc"], utc=True).to_pydatetime()

            best = None
            best_offset_seconds = None
            valid_samples = 0

            for offset in offsets:
                timestamp = center + timedelta(seconds=offset)

                iss_state = propagate_at(iss_satellite, timestamp)
                candidate_state = propagate_at(candidate_satellite, timestamp)

                if iss_state is None or candidate_state is None:
                    continue

                iss_position, iss_velocity = iss_state
                candidate_position, candidate_velocity = candidate_state

                distance_km = float(np.linalg.norm(candidate_position - iss_position))

                relative_speed_km_s = float(np.linalg.norm(candidate_velocity - iss_velocity))

                valid_samples += 1

                if best is None or distance_km < best["distance_km"]:
                    best = {
                        "timestamp": timestamp,
                        "distance_km": distance_km,
                        "relative_speed_km_s": relative_speed_km_s,
                    }
                    best_offset_seconds = offset

            # if best is None:
            #     failed.append((norad_id, "No valid propagated samples"))
            #     continue

            refinement = find_minimum_separation(iss_satellite, candidate_satellite,center)

            if refinement is None:
                failed.append((norad_id, "No valid propagated samples"))
                continue

            best = refinement

            results.append({
                "norad_id": norad_id,
                "object_name": object_name,
                "screening_time_utc": pd.to_datetime(sample["timestamp_utc"], utc=True),
                "screening_distance_km": float(sample["distance_km"]),
                "refined_tca_estimate_utc": pd.to_datetime(best["timestamp"], utc=True),
                "refined_min_distance_km": best["distance_km"],
                "relative_speed_km_s": best["relative_speed_km_s"],
                "candidate_element_epoch_utc": candidate_epoch,
                "candidate_epoch_offset_hours": (
                    best["timestamp"] - candidate_epoch.to_pydatetime()
                ).total_seconds() / 3600,
                "iss_element_epoch_utc": iss_epoch,
                "iss_epoch_offset_hours": (
                    best["timestamp"] - iss_epoch.to_pydatetime()
                ).total_seconds() / 3600,
                "valid_refinement_samples": best["valid_samples"],
                "refinement_step_seconds": STEP_SECONDS,
                "refinement_window_minutes": WINDOW_MINUTES,
                "refinement_boundary_minimum": best["refinement_boundary_minimum"],
                "refinement_status": best["refinement_status"],
                "epoch_quality": classify_epoch_quality(
                    (best["timestamp"] - candidate_epoch.to_pydatetime()).total_seconds() / 3600),
                "iss_epoch_quality": classify_epoch_quality(
                    (best["timestamp"] - iss_epoch.to_pydatetime()).total_seconds() / 3600),
                "overall_epoch_quality": max([
                    classify_epoch_quality((best["timestamp"] - candidate_epoch.to_pydatetime()).total_seconds() / 3600),
                    classify_epoch_quality((best["timestamp"] - iss_epoch.to_pydatetime()).total_seconds() / 3600),
                    ],key=lambda quality: QUALITY_RANK[quality],),
            })

        except Exception as exc:
            failed.append((norad_id, str(exc)))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    refined = pd.DataFrame(results)

    if not refined.empty:
        refined = refined.sort_values("refined_min_distance_km").reset_index(drop=True)

    refined.to_parquet(OUTPUT_FILE, index=False)

    print("\nRefinement completed.")
    print("Successful candidates:", len(refined))
    print("Failed candidates:", len(failed))
    print("Output:", OUTPUT_FILE)

    if not refined.empty:
        print("\nClosest refined approaches:")
        print(
            refined[
                [
                    "norad_id",
                    "object_name",
                    "refined_tca_estimate_utc",
                    "refined_min_distance_km",
                    "relative_speed_km_s",
                ]
            ].head(10).to_string(index=False)
        )

    if failed:
        print("\nFirst failures:")
        for norad_id, reason in failed[:10]:
            print(norad_id, reason)


if __name__ == "__main__":
    main()



