
from datetime import datetime, timezone

import numpy as np

from src.propagation.propagate_candidates import propagate_satellite
from src.propagation.refine_close_approaches import (
    initialize_satellite,
    propagate_at,
    classify_epoch_quality,
)


def make_omm_record():
    """Create a synthetic OMM record for testing SGP4."""

    return {
        "OBJECT_NAME": "TEST SATELLITE",
        "OBJECT_ID": "1998-067A",
        "CENTER_NAME": "EARTH",
        "REF_FRAME": "TEME",
        "TIME_SYSTEM": "UTC",
        "MEAN_ELEMENT_THEORY": "SGP4",
        "EPOCH": "2026-11-02T10:25:21.580320",
        "MEAN_MOTION": 15.5,
        "ECCENTRICITY": 0.001,
        "INCLINATION": 51.6,
        "RA_OF_ASC_NODE": 120.0,
        "ARG_OF_PERICENTER": 90.0,
        "MEAN_ANOMALY": 180.0,
        "EPHEMERIS_TYPE": 0,
        "CLASSIFICATION_TYPE": "U",
        "NORAD_CAT_ID": 50001,
        "ELEMENT_SET_NO": 999,
        "REV_AT_EPOCH": 1,
        "BSTAR": 0.0001,
        "MEAN_MOTION_DOT": 0.00001,
        "MEAN_MOTION_DDOT": 0.0,
    }


TEST_TIMESTAMP = datetime(
    2026, 11, 2, 10, 25, 21, 580320,
    tzinfo=timezone.utc,
)


# --------------------------------
# Candidate propagation tests
# --------------------------------

def test_candidate_propagation_returns_valid_state():
    record = make_omm_record()

    result = propagate_satellite(record, [TEST_TIMESTAMP])

    assert len(result) == 1

    row = result[0]

    assert row["norad_id"] == 50001
    assert row["object_name"] == "TEST SATELLITE"
    assert row["timestamp_utc"] == TEST_TIMESTAMP

    position = [row["x_km"], row["y_km"], row["z_km"]]
    velocity = [row["vx_km_s"], row["vy_km_s"], row["vz_km_s"]]

    assert np.all(np.isfinite(position))
    assert np.all(np.isfinite(velocity))


def test_candidate_propagation_returns_empty_for_no_timestamps():
    record = make_omm_record()

    result = propagate_satellite(record, [])

    assert result == []


# --------------------------------
# Refined propagation tests
# --------------------------------

def test_initialize_satellite():
    satellite = initialize_satellite(make_omm_record())

    assert satellite is not None


def test_propagate_at_returns_position_and_velocity():
    satellite = initialize_satellite(make_omm_record())

    result = propagate_at(satellite, TEST_TIMESTAMP)

    assert result is not None

    position, velocity = result

    assert position.shape == (3,)
    assert velocity.shape == (3,)

    assert np.all(np.isfinite(position))
    assert np.all(np.isfinite(velocity))


def test_propagate_at_handles_sgp4_error():
    class FailedSatellite:
        def sgp4(self, jd, fraction):
            return 1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)

    result = propagate_at(FailedSatellite(), TEST_TIMESTAMP)

    assert result is None


def test_propagate_at_handles_non_finite_values():
    class InvalidSatellite:
        def sgp4(self, jd, fraction):
            return 0, (float("nan"), 0.0, 0.0), (0.0, 0.0, 0.0)

    result = propagate_at(InvalidSatellite(), TEST_TIMESTAMP)

    assert result is None


# --------------------------------
# Orbital epoch quality tests
# --------------------------------

def test_epoch_quality_classification():
    assert classify_epoch_quality(12) == "acceptable"
    assert classify_epoch_quality(36) == "stale"
    assert classify_epoch_quality(60) == "very_stale"
    assert classify_epoch_quality(96) == "highly_stale"


def test_epoch_quality_uses_absolute_offset():
    assert classify_epoch_quality(-12) == "acceptable"
    assert classify_epoch_quality(-36) == "stale"
