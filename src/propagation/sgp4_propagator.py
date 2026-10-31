
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from sgp4 import omm
from sgp4.api import Satrec, jday, SGP4_ERRORS, WGS72


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (PROJECT_ROOT / "data" / "raw" / "iss" / "iss_gp_snapshot.json")

OUTPUT_FILE = (PROJECT_ROOT / "data" / "processed" / "iss" / "iss_propagated_positions.parquet")

STEP_MINUTES = 5
FORECAST_HOURS = 24
EXPECTED_NORAD_ID = 25544


def load_iss_orbit():
    """Load the ISS orbital elements saved from CelesTrak."""

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        snapshot = json.load(file)

    record = snapshot["orbital_data"]

    norad_id = int(record["NORAD_CAT_ID"])

    if norad_id != EXPECTED_NORAD_ID:
        raise ValueError(
            f"Expected ISS NORAD ID {EXPECTED_NORAD_ID}, "
            f"but received {norad_id}"
        )

    satellite = Satrec()
    omm.initialize(satellite, record, WGS72)

    epoch = datetime.fromisoformat(
        record["EPOCH"].replace("Z", "+00:00")
    )

    if epoch.tzinfo is None:
        epoch = epoch.replace(tzinfo=timezone.utc)
    else:
        epoch = epoch.astimezone(timezone.utc)

    return satellite, epoch, snapshot


def propagate_iss():
    """Propagate the ISS orbit for 24 hours at 5-minute intervals."""

    satellite, epoch, snapshot = load_iss_orbit()

    total_steps = FORECAST_HOURS * 60 // STEP_MINUTES

    records = []

    for step in range(total_steps + 1):
        timestamp = epoch + timedelta(minutes=step * STEP_MINUTES)

        jd, fraction = jday(
            timestamp.year,
            timestamp.month,
            timestamp.day,
            timestamp.hour,
            timestamp.minute,
            timestamp.second
            + timestamp.microsecond / 1_000_000,
        )

        error_code, position, velocity = satellite.sgp4(jd, fraction)

        if error_code != 0:
            raise RuntimeError(
                f"SGP4 propagation failed at {timestamp.isoformat()}: "
                f"{SGP4_ERRORS.get(error_code, 'Unknown SGP4 error')}"
            )

        records.append(
            {
                "timestamp_utc": timestamp,
                "norad_id": EXPECTED_NORAD_ID,
                "x_km": position[0],
                "y_km": position[1],
                "z_km": position[2],
                "vx_km_s": velocity[0],
                "vy_km_s": velocity[1],
                "vz_km_s": velocity[2],
            }
        )

    df = pd.DataFrame(records)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_FILE, index=False)


    ## Metadata
    ## --------------------------------------------
    metadata = {
        "norad_id": EXPECTED_NORAD_ID,
        "source": "CelesTrak GP OMM",
        "retrieved_at_utc": snapshot["retrieved_at_utc"],
        "element_epoch_utc": epoch.isoformat(),
        "propagation_model": "SGP4",
        "gravity_model": "WGS72",
        "coordinate_frame": "TEME",
        "time_system": "UTC",
        "position_unit": "km",
        "velocity_unit": "km/s",
        "start_time_utc": df["timestamp_utc"].iloc[0].isoformat(),
        "end_time_utc": df["timestamp_utc"].iloc[-1].isoformat(),
        "step_minutes": STEP_MINUTES,
        "number_of_records": len(df),
        "output_file": OUTPUT_FILE.name,
    }

    metadata_file = OUTPUT_FILE.with_name("iss_propagation_metadata.json")

    metadata_file.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"Metadata saved to: {metadata_file}")

    print("ISS orbit propagation completed.")
    print(f"NORAD ID: {EXPECTED_NORAD_ID}")
    print(f"Element epoch (UTC): {epoch.isoformat()}")
    print(f"Propagation interval: {STEP_MINUTES} minutes")
    print(f"Propagation duration: {FORECAST_HOURS} hours")
    print(f"Output shape: {df.shape}")
    print(f"Output file: {OUTPUT_FILE}")
    print("\nFirst 5 positions:")
    print(df.head().to_string(index=False))
    print("\nLast position:")
    print(df.tail(1).to_string(index=False))


if __name__ == "__main__":
    propagate_iss()
