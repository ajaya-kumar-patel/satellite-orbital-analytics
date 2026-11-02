
import numpy as np
import pandas as pd
import pytest

from src.propagation.validate_propagation import validate_propagation_data


@pytest.fixture
def valid_iss_data():
    timestamps = pd.date_range(
        "2026-11-02T10:25:00Z",
        periods=289,
        freq="5min",
    )

    return pd.DataFrame({
        "timestamp_utc": timestamps,
        "norad_id": [25544] * 289,
        "x_km": [6771.0] * 289,
        "y_km": [0.0] * 289,
        "z_km": [0.0] * 289,
        "vx_km_s": [0.0] * 289,
        "vy_km_s": [7.66] * 289,
        "vz_km_s": [0.0] * 289,
    })


def test_valid_iss_propagation_passes(valid_iss_data):
    report = validate_propagation_data(valid_iss_data)

    assert report["rows"] == 289
    assert report["unique_norad_ids"] == 1
    assert report["position_min_km"] == pytest.approx(6771.0)
    assert report["velocity_min_km_s"] == pytest.approx(7.66)


def test_missing_required_column_raises_error(valid_iss_data):
    data = valid_iss_data.drop(columns=["x_km"])

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_propagation_data(data)


def test_incorrect_row_count_raises_error(valid_iss_data):
    data = valid_iss_data.iloc[:-1]

    with pytest.raises(ValueError, match="Expected 289 rows"):
        validate_propagation_data(data)


def test_wrong_norad_id_raises_error(valid_iss_data):
    data = valid_iss_data.copy()
    data["norad_id"] = 12345

    with pytest.raises(ValueError, match="Unexpected satellite NORAD ID"):
        validate_propagation_data(data)


def test_duplicate_timestamps_raise_error(valid_iss_data):
    data = valid_iss_data.copy()
    data.loc[1, "timestamp_utc"] = data.loc[0, "timestamp_utc"]

    with pytest.raises(ValueError, match="monotonically increasing|Duplicate timestamps"):
        validate_propagation_data(data)


def test_non_finite_position_raises_error(valid_iss_data):
    data = valid_iss_data.copy()
    data.loc[0, "x_km"] = np.nan

    with pytest.raises(ValueError, match="Non-finite"):
        validate_propagation_data(data)


def test_invalid_position_magnitude_raises_error(valid_iss_data):
    data = valid_iss_data.copy()
    data["x_km"] = 100.0

    with pytest.raises(ValueError, match="Position magnitude"):
        validate_propagation_data(data)


def test_invalid_velocity_magnitude_raises_error(valid_iss_data):
    data = valid_iss_data.copy()
    data["vy_km_s"] = 20.0

    with pytest.raises(ValueError, match="Velocity magnitude"):
        validate_propagation_data(data)


def test_incorrect_time_interval_raises_error(valid_iss_data):
    data = valid_iss_data.copy()
    data.loc[1:, "timestamp_utc"] += pd.Timedelta(minutes=1)

    with pytest.raises(ValueError, match="timestamp intervals"):
        validate_propagation_data(data)
