
import numpy as np
import pandas as pd
import pytest

from src.propagation.validate_refined_approaches import validate_refined_data


@pytest.fixture
def sample_data():
    screening = pd.DataFrame({
        "norad_id": [10001, 10001, 10002, 10003],
        "distance_km": [50.0, 30.0, 60.0, 80.0],
    })

    refined = pd.DataFrame({
        "norad_id": [10001, 10002],
        "refined_min_distance_km": [20.0, 45.0],
        "relative_speed_km_s": [7.5, 6.8],
        "overall_epoch_quality": ["acceptable", "stale"],
        "refinement_status": ["interior_minimum", "boundary_minimum"],
        "refinement_boundary_minimum": [False, True],
    })

    return screening, refined


def test_valid_refined_data(sample_data):
    screening, refined = sample_data

    report = validate_refined_data(screening, refined)

    assert report["screening_candidates"] == 3
    assert report["refined_candidates"] == 2
    assert report["missing_candidates"] == 1
    assert report["minimum_distance_km"] == pytest.approx(20.0)
    assert report["maximum_distance_km"] == pytest.approx(45.0)
    assert report["boundary_minima"] == 1


def test_duplicate_refined_norad_ids_raise_error(sample_data):
    screening, refined = sample_data
    refined = pd.concat([refined, refined.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="Duplicate refined NORAD IDs"):
        validate_refined_data(screening, refined)


def test_unexpected_candidate_raises_error(sample_data):
    screening, refined = sample_data
    refined.loc[0, "norad_id"] = 99999

    with pytest.raises(ValueError, match="Unexpected candidates"):
        validate_refined_data(screening, refined)


def test_negative_distance_raises_error(sample_data):
    screening, refined = sample_data
    refined.loc[0, "refined_min_distance_km"] = -1.0

    with pytest.raises(ValueError, match="Negative refined distances"):
        validate_refined_data(screening, refined)


def test_non_finite_distance_raises_error(sample_data):
    screening, refined = sample_data
    refined.loc[0, "refined_min_distance_km"] = np.inf

    with pytest.raises(ValueError, match="Non-finite refined distances"):
        validate_refined_data(screening, refined)


def test_negative_relative_speed_raises_error(sample_data):
    screening, refined = sample_data
    refined.loc[0, "relative_speed_km_s"] = -1.0

    with pytest.raises(ValueError, match="Negative relative speeds"):
        validate_refined_data(screening, refined)


def test_missing_required_value_raises_error(sample_data):
    screening, refined = sample_data
    refined.loc[0, "overall_epoch_quality"] = None

    with pytest.raises(ValueError, match="Missing values"):
        validate_refined_data(screening, refined)


def test_empty_refined_dataset_raises_error(sample_data):
    screening, refined = sample_data
    refined = refined.iloc[0:0]

    with pytest.raises(ValueError, match="Refined dataset is empty"):
        validate_refined_data(screening, refined)
