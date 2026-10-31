
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (PROJECT_ROOT / "data" / "raw" / "iss" / "candidate_satellites_snapshot.json")

ISS_NORAD_ID = 25544

REQUIRED_FIELDS = ["NORAD_CAT_ID","OBJECT_NAME", "EPOCH", "MEAN_MOTION", "ECCENTRICITY", 
                   "INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY"]


def validate_candidate_satellites():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        snapshot = json.load(file)

    satellites = snapshot.get("orbital_data")

    if not isinstance(satellites, list) or not satellites:
        raise ValueError("Candidate satellite list is empty or invalid.")

    df = pd.DataFrame(satellites)

    missing_columns = set(REQUIRED_FIELDS) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required fields: {sorted(missing_columns)}")

    df["NORAD_CAT_ID"] = pd.to_numeric(df["NORAD_CAT_ID"], errors="coerce")

    if df["NORAD_CAT_ID"].isna().any():
        raise ValueError("Missing or invalid NORAD catalog IDs found.")

    if df["NORAD_CAT_ID"].duplicated().any():
        duplicates = df.loc[df["NORAD_CAT_ID"].duplicated(keep=False), "NORAD_CAT_ID"].tolist()
        raise ValueError(f"Duplicate NORAD IDs found: {duplicates[:10]}")

    if (df["NORAD_CAT_ID"] == ISS_NORAD_ID).any():
        raise ValueError("The ISS is present in its own candidate catalog.")

    numeric_fields = ["MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE", 
                      "ARG_OF_PERICENTER", "MEAN_ANOMALY"]

    for field in numeric_fields:
        df[field] = pd.to_numeric(df[field], errors="coerce")

        if df[field].isna().any():
            raise ValueError(f"Invalid numeric values in {field}.")

    if not df["MEAN_MOTION"].gt(0).all():
        raise ValueError("Non-positive mean motion found.")

    if not df["ECCENTRICITY"].between(0, 1, inclusive="left").all():
        raise ValueError("Eccentricity outside the valid range [0, 1).")

    if not df["INCLINATION"].between(0, 180).all():
        raise ValueError("Inclination outside the valid range [0, 180].")

    epochs = pd.to_datetime(df["EPOCH"], utc=True, errors="coerce")

    if epochs.isna().any():
        raise ValueError("Invalid orbital epochs found.")

    print("Candidate satellite validation passed.")
    print(f"Candidate records: {len(df)}")
    print(f"Unique NORAD IDs: {df['NORAD_CAT_ID'].nunique()}")
    print(f"ISS excluded: {not (df['NORAD_CAT_ID'] == ISS_NORAD_ID).any()}")
    print(f"Missing required values: {int(df[REQUIRED_FIELDS].isna().sum().sum())}")
    print(f"Oldest element epoch: {epochs.min()}")
    print(f"Newest element epoch: {epochs.max()}")


if __name__ == "__main__":
    validate_candidate_satellites()
