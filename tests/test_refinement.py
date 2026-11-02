
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from src.propagation.refine_close_approaches import find_minimum_separation


class FakeSatellite:
    """Satellite with a controlled position and velocity."""

    def __init__(self, position_function, velocity=(0.0, 0.0, 0.0)):
        self.position_function = position_function
        self.velocity = np.array(velocity, dtype=float)


def fake_propagate_at(satellite, timestamp):
    position = satellite.position_function(timestamp)
    velocity = satellite.velocity

    if position is None:
        return None

    return np.array(position, dtype=float), velocity


@pytest.fixture
def center():
    return datetime(2026, 11, 2, 10, 25, tzinfo=timezone.utc)


def test_finds_minimum_separation_at_center(center, monkeypatch):
    iss = FakeSatellite(lambda t: (0, 0, 0))
    candidate = FakeSatellite(
        lambda t: (abs((t - center).total_seconds()), 0, 0)
    )

    monkeypatch.setattr(
        "src.propagation.refine_close_approaches.propagate_at",
        fake_propagate_at,
    )

    result = find_minimum_separation(
        iss, candidate, center, window_minutes=1, step_seconds=10
    )

    assert result["distance_km"] == pytest.approx(0.0)
    assert result["timestamp"] == center
    assert result["refinement_status"] == "interior_minimum"


def test_finds_minimum_separation_away_from_center(center, monkeypatch):
    iss = FakeSatellite(lambda t: (0, 0, 0))

    candidate = FakeSatellite(
        lambda t: (
            abs((t - (center + timedelta(seconds=20))).total_seconds()),
            0,
            0,
        )
    )

    monkeypatch.setattr(
        "src.propagation.refine_close_approaches.propagate_at",
        fake_propagate_at,
    )

    result = find_minimum_separation(
        iss, candidate, center, window_minutes=1, step_seconds=10
    )

    assert result["timestamp"] == center + timedelta(seconds=20)
    assert result["distance_km"] == pytest.approx(0.0)


def test_detects_boundary_minimum(center, monkeypatch):
    iss = FakeSatellite(lambda t: (0, 0, 0))

    candidate = FakeSatellite(
        lambda t: (
            100 + (t - center).total_seconds(),
            0,
            0,
        )
    )

    monkeypatch.setattr(
        "src.propagation.refine_close_approaches.propagate_at",
        fake_propagate_at,
    )

    result = find_minimum_separation(
        iss, candidate, center, window_minutes=1, step_seconds=10
    )

    assert result["best_offset_seconds"] == -60
    assert result["refinement_boundary_minimum"] is True
    assert result["refinement_status"] == "boundary_minimum"


def test_counts_valid_refinement_samples(center, monkeypatch):
    iss = FakeSatellite(lambda t: (0, 0, 0))
    candidate = FakeSatellite(lambda t: (10, 0, 0))

    monkeypatch.setattr(
        "src.propagation.refine_close_approaches.propagate_at",
        fake_propagate_at,
    )

    result = find_minimum_separation(
        iss, candidate, center, window_minutes=1, step_seconds=10
    )

    assert result["valid_samples"] == 13


def test_returns_none_when_all_propagation_samples_fail(center, monkeypatch):
    iss = FakeSatellite(lambda t: None)
    candidate = FakeSatellite(lambda t: (10, 0, 0))

    monkeypatch.setattr(
        "src.propagation.refine_close_approaches.propagate_at",
        fake_propagate_at,
    )

    result = find_minimum_separation(
        iss, candidate, center, window_minutes=1, step_seconds=10
    )

    assert result is None


def test_calculates_relative_speed(center, monkeypatch):
    iss = FakeSatellite(
        lambda t: (0, 0, 0),
        velocity=(1, 0, 0),
    )

    candidate = FakeSatellite(
        lambda t: (10, 0, 0),
        velocity=(4, 0, 0),
    )

    monkeypatch.setattr(
        "src.propagation.refine_close_approaches.propagate_at",
        fake_propagate_at,
    )

    result = find_minimum_separation(
        iss, candidate, center, window_minutes=1, step_seconds=10
    )

    assert result["relative_speed_km_s"] == pytest.approx(3.0)
