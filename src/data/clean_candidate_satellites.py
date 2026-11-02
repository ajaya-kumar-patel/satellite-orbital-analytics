
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "iss" / "candidate_satellites_snapshot.json"

OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "iss" / "clean_candidate_satellites.json"

ISS_NORAD_ID = 25544

ISS_COMPONENT_NAMES = {
    "ISS (UNITY)",
    "ISS (DESTINY)",
    "ISS (ZVEZDA)",
    "ISS (NAUKA)",
    "POISK",
    "ZARYA",
    "ISS (ZVEZDA SERVICE MODULE)",
}

EXCLUDED_NORAD_IDS = {68837, 100057, 100712, 100882, 101031}

ORBIT_FIELDS = [
    "EPOCH",
    "MEAN_MOTION",
    "ECCENTRICITY",
    "INCLINATION",
    "RA_OF_ASC_NODE",
    "ARG_OF_PERICENTER",
    "MEAN_ANOMALY",
    "BSTAR",
    "MEAN_MOTION_DOT",
    "MEAN_MOTION_DDOT",
]


def clean_candidate_records(records, source_snapshot=""):
    """Remove ISS-related records and exact duplicate orbital records."""

    original = pd.DataFrame(records)
    original_count = len(original)

    names = original["OBJECT_NAME"].fillna("").str.strip().str.upper()
    norad_ids = pd.to_numeric(original["NORAD_CAT_ID"], errors="coerce")

    excluded_names = {name.upper() for name in ISS_COMPONENT_NAMES}

    keep = (
        (norad_ids != ISS_NORAD_ID)
        & ~norad_ids.isin(EXCLUDED_NORAD_IDS)
        & ~names.isin(excluded_names)
    )

    filtered = original.loc[keep].copy()

    removed_iss = original_count - len(filtered)

    available_fields = [
        field for field in ORBIT_FIELDS
        if field in filtered.columns
    ]

    before_dedup = len(filtered)

    filtered = filtered.drop_duplicates(
        subset=available_fields,
        keep="first"
    )

    removed_duplicates = before_dedup - len(filtered)

    return {
        "source_snapshot": source_snapshot,
        "target_norad_id": ISS_NORAD_ID,
        "candidate_count": len(filtered),
        "excluded_iss_related_records": removed_iss,
        "removed_exact_orbital_duplicates": removed_duplicates,
        "orbital_data": filtered.to_dict(orient="records"),
    }


def main():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        snapshot = json.load(file)

    result = clean_candidate_records(
        snapshot["orbital_data"],
        source_snapshot=str(INPUT_FILE),
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    print("Candidate catalog cleaning completed.")
    print(f"Original records: {len(snapshot['orbital_data'])}")
    print(f"Excluded ISS-related records: {result['excluded_iss_related_records']}")
    print(f"Exact orbital duplicates removed: {result['removed_exact_orbital_duplicates']}")
    print(f"Remaining candidates: {result['candidate_count']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
