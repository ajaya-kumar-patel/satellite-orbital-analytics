import json
from datetime import datetime, timezone
from pathlib import Path

import requests

ISS_NORAD_ID = 25544

CELESTRAK_URL = (
    "https://celestrak.org/NORAD/elements/gp.php"
    f"?CATNR={ISS_NORAD_ID}&FORMAT=JSON"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "iss"
SNAPSHOT_FILE = DATA_DIR / "iss_gp_snapshot.json"


def fetch_iss_data() -> dict:
    """Fetch and validate the latest available ISS GP orbital record."""

    response = requests.get(
        CELESTRAK_URL,
        timeout=30,
        headers={"User-Agent": "ISS-Conjunction-Risk-Analysis/1.0"},
    )

    response.raise_for_status()

    records = response.json()

    if not isinstance(records, list) or len(records) != 1:
        raise ValueError(
            f"Expected one ISS orbital record, received "
            f"{len(records) if isinstance(records, list) else 'invalid response'}."
        )

    record = records[0]

    if str(record.get("NORAD_CAT_ID", "")).strip() != str(ISS_NORAD_ID):
        raise ValueError("The returned record is not the ISS (NORAD ID 25544).")

    if not record.get("EPOCH"):
        raise ValueError("The orbital record is missing its epoch.")

    required_fields = ["INCLINATION", "RA_OF_ASC_NODE", "ECCENTRICITY",
                       "ARG_OF_PERICENTER", "MEAN_ANOMALY", "MEAN_MOTION"]

    missing = [field for field in required_fields if field not in record]

    if missing:
        raise ValueError(f"Missing orbital fields: {missing}")

    return record


def save_snapshot(record: dict) -> Path:
    """Save the orbital record and its retrieval timestamp."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": CELESTRAK_URL,
        "norad_catalog_id": ISS_NORAD_ID,
        "orbital_data": record,
    }

    SNAPSHOT_FILE.write_text(
        json.dumps(snapshot, indent=2),
        encoding="utf-8",
    )

    return SNAPSHOT_FILE

def main() -> None:
    """Fetch the ISS record and save a new local snapshot."""

    print("Fetching ISS orbital data from CelesTrak...")

    try:
        record = fetch_iss_data()
        snapshot_path = save_snapshot(record)

        print("ISS orbital data fetched successfully.")
        print(f"NORAD ID: {record['NORAD_CAT_ID']}")
        print(f"Element epoch: {record['EPOCH']}")
        print(f"Snapshot saved to: {snapshot_path}")

    except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ISS data fetch failed: {exc}") from exc


if __name__ == "__main__":
    main()