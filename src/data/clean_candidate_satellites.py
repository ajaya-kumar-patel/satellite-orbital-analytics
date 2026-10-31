import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (PROJECT_ROOT / "data" / "raw" / "iss" / "candidate_satellites_snapshot.json")

OUTPUT_FILE = (PROJECT_ROOT / "data" / "processed" / "iss" / "clean_candidate_satellites.json")

ISS_NORAD_ID = 25544

# These are components of the ISS, not independent conjunction targets.
ISS_COMPONENT_NAMES = {"ISS (UNITY)", "ISS (DESTINY)", "ISS (ZVEZDA)", "ISS (NAUKA)",
                       "POISK", "ZARYA", "ISS (ZVEZDA SERVICE MODULE)"}

# Known docked ISS visiting vehicle; not an independent conjunction target.
EXCLUDED_NORAD_IDS = {68837, 100057, 100712, 100882, 101031}
# PROGRESS-MS 34, SOYUZ-MS 29, PROGRESS-MS 35, CREW DRAGON 13, DRAGON CRS-35

# Fields used to identify exactly duplicated orbital records.
ORBIT_FIELDS = ["EPOCH", "MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE", 
                "ARG_OF_PERICENTER", "MEAN_ANOMALY", "BSTAR", "MEAN_MOTION_DOT",
                "MEAN_MOTION_DDOT"]


def main():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        snapshot = json.load(file)

    original = pd.DataFrame(snapshot["orbital_data"])
    original_count = len(original)

    # Remove the target itself and named ISS components.
    names = original["OBJECT_NAME"].fillna("").str.strip().str.upper()

    excluded_names = {name.upper() for name in ISS_COMPONENT_NAMES}

    norad_ids = pd.to_numeric(original["NORAD_CAT_ID"], errors="coerce")

    keep = (
        (norad_ids != ISS_NORAD_ID)
        & ~norad_ids.isin(EXCLUDED_NORAD_IDS)
        & ~names.isin(excluded_names)
    )

    filtered = original.loc[keep].copy()
    removed_iss = original_count - len(filtered)

    # Drop exact duplicates in the orbital-element records.
    available_fields = [field for field in ORBIT_FIELDS if field in filtered.columns]

    before_dedup = len(filtered)

    filtered = filtered.drop_duplicates(subset=available_fields, keep="first")

    removed_duplicates = before_dedup - len(filtered)

    result = {
        "source_snapshot": str(INPUT_FILE),
        "target_norad_id": ISS_NORAD_ID,
        "candidate_count": len(filtered),
        "excluded_iss_related_records": removed_iss,
        "removed_exact_orbital_duplicates": removed_duplicates,
        "orbital_data": filtered.to_dict(orient="records"),
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    print("Candidate catalog cleaning completed.")
    print(f"Original records: {original_count}")
    print(f"Excluded ISS-related records: {removed_iss}")
    print(f"Exact orbital duplicates removed: {removed_duplicates}")
    print(f"Remaining candidates: {len(filtered)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
