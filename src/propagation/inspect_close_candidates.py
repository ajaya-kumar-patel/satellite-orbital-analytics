
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CATALOG_FILE = (PROJECT_ROOT / "data" / "raw" / "iss" / "candidate_satellites_snapshot.json")

CLOSE_FILE = (PROJECT_ROOT / "data" / "processed" / "iss" / "close_approach_screening.parquet")

ISS_NORAD_ID = 25544

def main():
    with CATALOG_FILE.open("r", encoding="utf-8") as file:
        snapshot = json.load(file)

    catalog = pd.DataFrame(snapshot["orbital_data"])
    close = pd.read_parquet(CLOSE_FILE)

    # Find the ISS record in the original ISS snapshot.
    iss_file = (PROJECT_ROOT / "data" / "raw" / "iss" / "iss_gp_snapshot.json")

    with iss_file.open("r", encoding="utf-8") as file:
        iss_record = json.load(file)["orbital_data"]

    numeric_fields = ["MEAN_MOTION", "ECCENTRICITY", "INCLINATION",
                      "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY"]

    print("ISS orbital elements:")
    for field in numeric_fields:
        print(f"{field}: {iss_record.get(field)}")

    print("\nTen closest screening records:")
    closest = close.nsmallest(10, "distance_km")
    print(closest[["timestamp_utc", "norad_id", "object_name", "distance_km"]].to_string(index=False))

    close_ids = close["norad_id"].unique()

    print("\nCandidate orbital elements for closest objects:")
    columns = ["NORAD_CAT_ID", "OBJECT_NAME", "EPOCH", *numeric_fields]

    print(
        catalog[catalog["NORAD_CAT_ID"].isin(close_ids)][columns]
        .head(30)
        .to_string(index=False)
    )

    # Identify records with identical mean-motion and eccentricity values
    # to the ISS, as a diagnostic only.
    same_elements = catalog[
        (catalog["MEAN_MOTION"].astype(str)
         == str(iss_record.get("MEAN_MOTION")))
        & (catalog["ECCENTRICITY"].astype(str)
           == str(iss_record.get("ECCENTRICITY")))
    ]

    print("\nCandidates with exactly matching mean motion and eccentricity:")
    print(
        same_elements[["NORAD_CAT_ID", "OBJECT_NAME", "EPOCH"]]
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
