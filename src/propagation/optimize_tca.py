import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sgp4 import omm
from sgp4.api import Satrec, WGS72, jday


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ISS_SNAPSHOT = PROJECT_ROOT / "data/raw/iss/iss_gp_snapshot.json"
CANDIDATE_CATALOG = (PROJECT_ROOT / "data/processed/iss/clean_candidate_satellites.json")
REFINED_FILE = (PROJECT_ROOT / "data/processed/iss/close_approach_refined.parquet")

TARGET_NORAD_ID = 48380  # STARLINK-2614
WINDOW_SECONDS = 60

# Optimizer configuration
OPTIMIZER_METHOD = "bounded"
XATOL_SECONDS = 1e-6


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

    center = pd.to_datetime(target["refined_tca_estimate_utc"], utc=True).to_pydatetime()

    iss_record = iss_data["orbital_data"]

    candidate_records = {
        int(record["NORAD_CAT_ID"]): record
        for record in catalog_data["orbital_data"]
    }

    candidate_record = candidate_records.get(TARGET_NORAD_ID)

    if candidate_record is None:
        raise ValueError(f"NORAD {TARGET_NORAD_ID} not found in candidate catalog")

    iss_satellite = initialize_satellite(iss_record)
    candidate_satellite = initialize_satellite(candidate_record)

    def separation_at_offset(offset_seconds):
        timestamp = center + timedelta(seconds=float(offset_seconds))

        iss_state = propagate_at(iss_satellite, timestamp)
        candidate_state = propagate_at(candidate_satellite, timestamp)

        if iss_state is None or candidate_state is None:
            raise RuntimeError(
                f"Invalid SGP4 propagation at offset {offset_seconds:.9f} s"
            )

        iss_position, _ = iss_state
        candidate_position, _ = candidate_state

        return float(
            np.linalg.norm(candidate_position - iss_position)
        )

    lower_bound = -WINDOW_SECONDS
    upper_bound = WINDOW_SECONDS

    result = minimize_scalar(
        separation_at_offset,
        bounds=(lower_bound, upper_bound),
        method=OPTIMIZER_METHOD,
        options={"xatol": XATOL_SECONDS},
    )

    if not result.success:
        raise RuntimeError(
            f"TCA optimization failed: {result.message}"
        )

    optimized_offset = float(result.x)
    optimized_distance = float(result.fun)
    optimized_tca = center + timedelta(seconds=optimized_offset)

    # Explicitly inspect both search boundaries.
    lower_distance = separation_at_offset(lower_bound)
    upper_distance = separation_at_offset(upper_bound)

    boundary_tolerance_km = 1e-9

    boundary_minimum = (
        optimized_distance >= min(lower_distance, upper_distance)
        - boundary_tolerance_km
    )

    print(f"Target: {target['object_name']} ({TARGET_NORAD_ID})")
    print(f"Original TCA estimate: {center.isoformat()}")
    print(f"Search window: +/- {WINDOW_SECONDS} seconds")

    print("\nCONTINUOUS-TIME OPTIMIZATION")
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Function evaluations: {result.nfev}")
    print(f"Optimized offset: {optimized_offset:.9f} seconds")
    print(f"Optimized TCA: {optimized_tca.isoformat()}")
    print(f"Minimum separation: {optimized_distance:.9f} km")

    print("\nBOUNDARY CHECK")
    print(f"Lower boundary separation: {lower_distance:.9f} km")
    print(f"Upper boundary separation: {upper_distance:.9f} km")
    print(f"Boundary minimum suspected: {boundary_minimum}")

    print("\nCOMPARISON WITH PREVIOUS RESULTS")
    print(
        f"10-second minimum: "
        f"{target['refined_min_distance_km']:.9f} km"
    )
    print(
        f"Difference from previous refinement: "
        f"{optimized_distance - float(target['refined_min_distance_km']):+.9f} km"
    )


if __name__ == "__main__":
    main()
