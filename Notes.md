# ISS Conjunction Analysis and Collision Risk Assessment — Personal Execution Notes

**Project:** ISS Close-Approach Screening  
**Target:** ISS (ZARYA), NORAD ID 25544  
**Data source:** CelesTrak  
**Propagation:** SGP4 using OMM orbital elements  
**Coordinate frame:** TEME

---

## Phase 1 — Data collection and initial propagation

1. Run `fetch_celestrak.py` to download the targeted ISS orbital elements.

   Output: `data/raw/iss/iss_gp_snapshot.json`

2. Run `fetch_candidate_satellites.py` to download the candidate satellite catalog.

   Output: `data/raw/iss/candidate_satellites_snapshot.json`

3. Run `validate_candidate_satellites.py` to validate the downloaded candidate catalog.

4. Run `sgp4_propagator.py` to propagate the ISS trajectory over 24 hours using 5-minute intervals.

   Output: `data/processed/iss/iss_propagated_positions.parquet`

5. Run `validate_propagation.py` to validate the ISS propagation results.

6. Run `propagate_candidates.py` to propagate all candidate satellites at the same timestamps as the ISS.

   Output: `data/processed/iss/candidate_propagated_positions.parquet`

7. Run `find_close_approaches.py` to perform broad screening using a 100 km separation threshold.

   Output: `data/processed/iss/close_approach_screening.parquet`

   Initial screening results:
   - 4,856,067 matched position records
   - 160 screening samples within 100 km
   - 146 unique candidate satellites

---

## Phase 2 — Candidate inspection and cleaning

8. Run `inspect_close_candidates.py` to inspect the closest candidates and investigate objects that may be ISS components or visiting vehicles.

9. Run `clean_candidate_satellites.py` to remove:
   - The ISS itself.
   - ISS components.
   - Duplicate orbital-element records.
   - Identified visiting or docked ISS vehicles.

10. Update the candidate catalog input in `propagate_candidates.py` to use:

    `data/processed/iss/clean_candidate_satellites.json`

11. Rerun `propagate_candidates.py` using the cleaned catalog.

12. Rerun `find_close_approaches.py` to regenerate the broad screening results using the cleaned candidate population.

13. If suspiciously close objects remain, rerun `inspect_close_candidates.py` and investigate their orbital elements and identity.

14. When a visiting vehicle is identified, verify its identity using available catalog information and add its NORAD ID to the exclusion set in `clean_candidate_satellites.py`.

15. Rerun the cleaning, candidate propagation and broad screening stages after changing the exclusion list.

**Important:** The visiting-vehicle exclusion list is manually curated and snapshot-specific. Do not treat it as an automatic or universally reliable docked-object detector.

---

## Phase 3 — Refined close-approach analysis

16. Run `refine_close_approaches.py`.

    This script:
    - Takes the closest 5-minute screening sample for each candidate.
    - Searches a ±10-minute window around that sample.
    - Uses 10-second intervals.
    - Propagates the ISS and candidate at matching timestamps.
    - Calculates separation and relative velocity.
    - Identifies the minimum sampled separation and estimated TCA.
    - Records orbital-element epoch offsets and quality labels.

    Output:

    `data/processed/iss/close_approach_refined.parquet`

17. Perform the refinement boundary check.

    - If the minimum occurs at the first or last refinement sample, flag the candidate.
    - If the minimum occurs inside the window, classify it as an interior minimum.
    - Investigate boundary cases using a wider refinement window.

    Current result:
    - 146 interior minima.
    - 0 boundary minima.

18. Run `validate_refined_approaches.py`.

    Validate:
    - Candidate coverage.
    - Unique NORAD IDs.
    - Missing values.
    - Finite and non-negative distances and relative velocities.
    - Epoch-quality distribution.
    - Screening versus refined separation.

---

## Phase 4 — Exploratory analysis

19. Open `notebooks/03_conjunction_analysis.ipynb`.

    Perform:
    - Separation versus time analysis.
    - Refined minimum separation distribution.
    - Relative velocity versus separation analysis.
    - Epoch-quality analysis.

20. Run `check_tca_time_resolution.py` for the closest candidate:

    **STARLINK-2614 — NORAD 48380**

    Compare different sampling intervals around the estimated TCA:

    - 10 seconds
    - 5 seconds
    - 1 second
    - 0.1 seconds

    Current results:

    | Time step | Minimum separation |
    |---|---:|
    | 10 s | 27.846792 km |
    | 5 s | 27.846792 km |
    | 1 s | 27.788392 km |
    | 0.1 s | 27.787749 km |

    The 0.1-second result is approximately 0.643 metres lower than the 1-second result.

---

## Current project status

- [x] ISS data collection
- [x] Candidate catalog collection
- [x] Candidate catalog validation
- [x] ISS SGP4 propagation
- [x] Candidate SGP4 propagation
- [x] Broad close-approach screening
- [x] Candidate inspection and cleaning
- [x] Refined close-approach analysis
- [x] Boundary-minimum check
- [x] Refined results validation
- [x] Exploratory notebook and visualizations
- [x] Time-resolution sensitivity check (0.1 seconds)
- [x] Continuous-time TCA optimization
- [ ] Further independent validation and documentation

**Important project limitation:** This is a preliminary, catalog-based conjunction-screening project. It is not an operational collision-avoidance system, validated conjunction assessment, or collision-probability estimation system.
