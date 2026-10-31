import json
from datetime import datetime, timezone
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_FILE = (PROJECT_ROOT / "data" / "raw" / "iss" / "candidate_satellites_snapshot.json")

# CelesTrak's active satellites group.
CELESTRAK_URL = (
    "https://celestrak.org/NORAD/elements/gp.php"
    "?GROUP=active&FORMAT=JSON"
)

ISS_NORAD_ID = 25544
REQUEST_TIMEOUT = 60

def fetch_candidate_satellites():
    print("Fetching active satellite orbital elements from CelesTrak...")

    response = requests.get(CELESTRAK_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    satellites = response.json()

    if not isinstance(satellites, list) or not satellites:
        raise ValueError("CelesTrak returned no satellite records.")

    # Exclude the ISS itself from the candidate list.
    candidates = [
        satellite
        for satellite in satellites
        if int(satellite.get("NORAD_CAT_ID", -1)) != ISS_NORAD_ID
    ]

    if not candidates:
        raise ValueError("No candidate satellites found.")

    snapshot = {
        "source": "CelesTrak active GP catalog",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_norad_id": ISS_NORAD_ID,
        "candidate_count": len(candidates),
        "orbital_data": candidates,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(snapshot, file, indent=2)

    print("Candidate satellite snapshot saved.")
    print(f"Total records received: {len(satellites)}")
    print(f"Candidate satellites: {len(candidates)}")
    print(f"ISS excluded: {all(int(s['NORAD_CAT_ID']) != ISS_NORAD_ID for s in candidates)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    fetch_candidate_satellites()

