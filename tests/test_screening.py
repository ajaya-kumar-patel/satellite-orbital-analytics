
import pandas as pd
import pytest

from src.propagation.find_close_approaches import screen_close_approaches


@pytest.fixture
def sample_positions():
    timestamp = pd.Timestamp("2026-11-02T10:25:00Z")

    iss = pd.DataFrame({
        "timestamp_utc": [timestamp],
        "x_km": [7000.0],
        "y_km": [0.0],
        "z_km": [0.0],
    })

    candidates = pd.DataFrame({
        "timestamp_utc": [timestamp, timestamp, timestamp],
        "norad_id": [10001, 10002, 10003],
        "object_name": ["SAT-A", "SAT-B", "SAT-C"],
        "x_km": [7010.0, 7050.0, 7200.0],
        "y_km": [0.0, 0.0, 0.0],
        "z_km": [0.0, 0.0, 0.0],
    })

    return candidates, iss


def test_screening_calculates_correct_distances(sample_positions):
    candidates, iss = sample_positions

    result = screen_close_approaches(candidates, iss)

    distances = result.set_index("norad_id")["distance_km"]

    assert distances.loc[10001] == pytest.approx(10.0)
    assert distances.loc[10002] == pytest.approx(50.0)


def test_screening_excludes_positions_outside_threshold(sample_positions):
    candidates, iss = sample_positions

    result = screen_close_approaches(candidates, iss, threshold_km=100.0)

    assert set(result["norad_id"]) == {10001, 10002}
    assert 10003 not in result["norad_id"].values


def test_screening_includes_exact_threshold_boundary(sample_positions):
    candidates, iss = sample_positions

    candidates.loc[0, "x_km"] = 7100.0

    result = screen_close_approaches(candidates, iss, threshold_km=100.0)

    assert 10001 in result["norad_id"].values


def test_screening_uses_matching_timestamps_only(sample_positions):
    candidates, iss = sample_positions

    candidates["timestamp_utc"] += pd.Timedelta(minutes=5)

    result = screen_close_approaches(candidates, iss)

    assert result.empty


def test_screening_returns_empty_when_no_candidates_are_close(sample_positions):
    candidates, iss = sample_positions

    candidates["x_km"] += 1000.0

    result = screen_close_approaches(candidates, iss)

    assert result.empty
