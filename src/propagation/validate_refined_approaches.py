from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCREENING_FILE = (PROJECT_ROOT / "data/processed/iss/close_approach_screening.parquet")

REFINED_FILE = (PROJECT_ROOT / "data/processed/iss/close_approach_refined.parquet")



def validate_refined_data(screening, refined):
    """Validate refined conjunction results against broad screening results."""

    screening_required = ["norad_id", "distance_km"]
    refined_required = [
        "norad_id",
        "refined_min_distance_km",
        "relative_speed_km_s",
        "overall_epoch_quality",
        "refinement_status",
        "refinement_boundary_minimum",
    ]

    missing_screening = set(screening_required) - set(screening.columns)
    missing_refined = set(refined_required) - set(refined.columns)

    if missing_screening:
        raise ValueError(f"Missing screening columns: {sorted(missing_screening)}")

    if missing_refined:
        raise ValueError(f"Missing refined columns: {sorted(missing_refined)}")

    if refined.empty:
        raise ValueError("Refined dataset is empty")

    distances = refined["refined_min_distance_km"].to_numpy(dtype=float)
    speeds = refined["relative_speed_km_s"].to_numpy(dtype=float)

    if not np.isfinite(distances).all():
        raise ValueError("Non-finite refined distances found")

    if not np.isfinite(speeds).all():
        raise ValueError("Non-finite relative speeds found")

    if (distances < 0).any():
        raise ValueError("Negative refined distances found")

    if (speeds < 0).any():
        raise ValueError("Negative relative speeds found")

    if refined["norad_id"].duplicated().any():
        raise ValueError("Duplicate refined NORAD IDs found")

    if refined[refined_required].isna().any().any():
        raise ValueError("Missing values found in required refined columns")

    screening_ids = set(screening["norad_id"].unique())
    refined_ids = set(refined["norad_id"].unique())

    unexpected_ids = refined_ids - screening_ids

    if unexpected_ids:
        raise ValueError(f"Unexpected candidates in refinement: {sorted(unexpected_ids)}")

    comparison = refined.merge(
        screening.groupby("norad_id")["distance_km"]
        .min()
        .rename("screening_min_distance_km"),
        on="norad_id",
        how="left",
        validate="one_to_one",
    )

    reduction = (
        comparison["screening_min_distance_km"]
        - comparison["refined_min_distance_km"]
    )

    return {
        "screening_candidates": len(screening_ids),
        "refined_candidates": len(refined_ids),
        "missing_candidates": len(screening_ids - refined_ids),
        "minimum_distance_km": distances.min(),
        "maximum_distance_km": distances.max(),
        "minimum_relative_speed_km_s": speeds.min(),
        "maximum_relative_speed_km_s": speeds.max(),
        "boundary_minima": int(refined["refinement_boundary_minimum"].sum()),
        "candidates_with_reduced_separation": int((reduction > 0).sum()),
    }


def main():
    for path in (SCREENING_FILE, REFINED_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    screening = pd.read_parquet(SCREENING_FILE)
    refined = pd.read_parquet(REFINED_FILE)

    report = validate_refined_data(screening, refined)
    print("\nRefined data validation passed.")
    print(report)

    print("=" * 65)
    print("ISS CLOSE-APPROACH REFINEMENT VALIDATION REPORT")
    print("=" * 65)

    # 1. Dataset counts
    print("\n1. DATASET SUMMARY")
    print("Screening samples:", len(screening))
    print("Unique screened candidates:", screening["norad_id"].nunique())
    print("Refined candidates:", len(refined))
    print("Unique refined candidates:", refined["norad_id"].nunique())

    # 2. Candidate coverage
    screening_ids = set(screening["norad_id"].unique())
    refined_ids = set(refined["norad_id"].unique())

    print("\n2. CANDIDATE COVERAGE")
    print("Screened candidates missing from refinement:", len(screening_ids - refined_ids))
    print("Unexpected candidates in refinement:", len(refined_ids - screening_ids))
    print("Duplicate refined NORAD IDs:", refined["norad_id"].duplicated().sum())

    # 3. Separation statistics
    distances = refined["refined_min_distance_km"]

    print("\n3. REFINED SEPARATION STATISTICS")
    print(f"Minimum: {distances.min():.3f} km")
    print(f"Median:  {distances.median():.3f} km")
    print(f"Mean:    {distances.mean():.3f} km")
    print(f"Maximum: {distances.max():.3f} km")

    # 4. Relative velocity statistics
    speeds = refined["relative_speed_km_s"]

    print("\n4. RELATIVE VELOCITY STATISTICS")
    print(f"Minimum: {speeds.min():.4f} km/s")
    print(f"Median:  {speeds.median():.4f} km/s")
    print(f"Mean:    {speeds.mean():.4f} km/s")
    print(f"Maximum: {speeds.max():.4f} km/s")

    # 5. Epoch quality
    print("\n5. OVERALL EPOCH QUALITY")
    print(refined["overall_epoch_quality"].value_counts().to_string())

    # 6. Boundary check
    print("\n6. REFINEMENT WINDOW CHECK")
    print(refined["refinement_status"].value_counts().to_string())
    print("Boundary minima:", int(refined["refinement_boundary_minimum"].sum()))

    # 7. Data integrity
    print("\n7. DATA INTEGRITY")
    print("Missing values:", int(refined.isna().sum().sum()))
    print("Non-finite distances:", int((~np.isfinite(distances)).sum()))
    print("Negative distances:", int((distances < 0).sum()))
    print("Non-finite relative speeds:", int((~np.isfinite(speeds)).sum()))
    print("Negative relative speeds:", int((speeds < 0).sum()))

    # 8. Refinement comparison
    comparison = refined.merge(
        screening.groupby("norad_id")["distance_km"]
        .min()
        .rename("screening_min_distance_km"),
        on="norad_id",
        how="left",
        validate="one_to_one",
    )

    reduction = (comparison["screening_min_distance_km"] - comparison["refined_min_distance_km"])

    print("\n8. SCREENING VS REFINED SEPARATION")
    print("Candidates with reduced separation:", int((reduction > 0).sum()))
    print("Candidates with unchanged separation:", int((reduction == 0).sum()))
    print(f"Largest reduction: {reduction.max():.3f} km")
    print(f"Mean reduction: {reduction.mean():.3f} km")

    print("\n" + "=" * 65)
    print("VALIDATION REPORT COMPLETED")
    print("=" * 65)


if __name__ == "__main__":
    main()
