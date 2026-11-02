
import pytest

from src.data.validate_candidate_satellites import validate_records
from src.data.clean_candidate_satellites import clean_candidate_records


def make_satellite(
    norad_id=50001,
    name="TEST SATELLITE",
    eccentricity=0.001,
):
    return {
        "NORAD_CAT_ID": norad_id,
        "OBJECT_NAME": name,
        "EPOCH": "2026-11-02T10:25:21.580320",
        "MEAN_MOTION": 15.5,
        "ECCENTRICITY": eccentricity,
        "INCLINATION": 51.6,
        "RA_OF_ASC_NODE": 120.0,
        "ARG_OF_PERICENTER": 90.0,
        "MEAN_ANOMALY": 180.0,
        "BSTAR": 0.0001,
        "MEAN_MOTION_DOT": 0.00001,
        "MEAN_MOTION_DDOT": 0.0,
    }


# -------------------------------
# Catalog validation tests
# -------------------------------

def test_valid_satellite_record():
    records = [make_satellite()]

    result = validate_records(records)

    assert len(result) == 1
    assert result.iloc[0]["NORAD_CAT_ID"] == 50001


def test_empty_catalog_raises_error():
    with pytest.raises(ValueError, match="empty or invalid"):
        validate_records([])


def test_duplicate_norad_ids_raise_error():
    records = [
        make_satellite(norad_id=50001),
        make_satellite(norad_id=50001),
    ]

    with pytest.raises(ValueError, match="Duplicate NORAD IDs"):
        validate_records(records)


def test_iss_in_candidate_catalog_raises_error():
    records = [make_satellite(norad_id=25544)]

    with pytest.raises(ValueError, match="ISS is present"):
        validate_records(records)


def test_invalid_eccentricity_raises_error():
    records = [make_satellite(eccentricity=1.2)]

    with pytest.raises(ValueError, match="Eccentricity"):
        validate_records(records)


# -------------------------------
# Catalog cleaning tests
# -------------------------------

def test_cleaning_removes_iss_and_excluded_objects():
    records = [
        make_satellite(norad_id=50001),
        make_satellite(norad_id=25544, name="ISS"),
        make_satellite(norad_id=68837, name="VISITING VEHICLE"),
        make_satellite(norad_id=50002, name="ZARYA"),
    ]

    result = clean_candidate_records(records)

    assert result["candidate_count"] == 1
    assert result["excluded_iss_related_records"] == 3
    assert result["orbital_data"][0]["NORAD_CAT_ID"] == 50001


def test_cleaning_removes_exact_orbital_duplicates():
    first = make_satellite(norad_id=50001)
    duplicate = make_satellite(norad_id=50002)

    records = [first, duplicate]

    result = clean_candidate_records(records)

    assert result["candidate_count"] == 1
    assert result["removed_exact_orbital_duplicates"] == 1


def test_cleaning_preserves_different_orbits():
    first = make_satellite(norad_id=50001)
    second = make_satellite(norad_id=50002, eccentricity=0.01)

    result = clean_candidate_records([first, second])

    assert result["candidate_count"] == 2
