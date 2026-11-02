# ISS Conjunction Screening and Orbital Analytics

A Python-based satellite orbital analytics pipeline for identifying and refining potential close approaches between the International Space Station (ISS) and objects in the satellite catalog.

The project uses orbital data from CelesTrak, SGP4 propagation, time-aligned position comparison, and refined minimum-separation estimation to perform preliminary conjunction screening.

## Project Overview

The objective is to build an end-to-end orbital analytics pipeline that:

- Retrieves ISS and catalog satellite orbital data.
- Validates and cleans satellite catalog records.
- Propagates satellite orbits over a 24-hour analysis window.
- Screens candidate satellites based on their distance from the ISS.
- Refines potential close approaches using higher temporal resolution.
- Validates the resulting close-approach dataset.

**Target object:** International Space Station (ISS), NORAD ID 25544.

**Data source:** CelesTrak General Perturbations (GP) orbital data.

## System Architecture

```text
                CelesTrak GP Data
                       |
             +---------+---------+
             |                   |
          ISS Data         Candidate Catalog
             |                   |
             |             Catalog Validation
             |                   |
             |              Data Cleaning
             |                   |
             +---------+---------+
                       |
                SGP4 Propagation
                       |
              ISS and Candidate
               Position Records
                       |
              Broad Close-Approach
                   Screening
                 (100 km)
                       |
              Close-Approach
                  Refinement
             (+/- 10 min, 10 sec)
                       |
              Refined Data
                 Validation
                       |
                Final Results
```

## Methodology

### 1. Orbital Data Acquisition

- Retrieve ISS orbital elements and candidate satellite catalog records from CelesTrak.
- Use OMM (Orbit Mean-Elements Message) records as propagation inputs.
- Exclude the ISS from the candidate catalog.
- Validate NORAD IDs, orbital parameters, missing values, and duplicate records.

### 2. Satellite Catalog Cleaning

- Remove known ISS-related objects and configured exclusions.
- Remove exact orbital duplicates.
- Preserve objects with distinct orbital elements.

### 3. Orbit Propagation

- Use the SGP4 propagator to calculate satellite positions and velocities.
- Propagate the ISS and candidate satellites over a 24-hour window.
- Use 5-minute sampling intervals for broad screening.
- Represent propagated states in the TEME coordinate frame.

### 4. Broad Close-Approach Screening

- Compare candidate satellite positions with ISS positions at matching timestamps.
- Calculate three-dimensional Euclidean separation:

$$
d = \sqrt{(x_c-x_{ISS})^2+(y_c-y_{ISS})^2+(z_c-z_{ISS})^2}
$$

- Retain candidate observations within a 100 km screening threshold.
- Identify unique candidate satellites for further analysis.

### 5. Close-Approach Refinement

- Re-propagate shortlisted candidates around their screening epochs.
- Use a refinement window of ±10 minutes.
- Apply a 10-second sampling interval.
- Identify minimum estimated separation and corresponding relative velocity.
- Flag minima occurring at refinement-window boundaries.

### 6. Data Validation

Validate the refined dataset for:

- Missing and non-finite values.
- Negative separation and relative velocity.
- Duplicate NORAD IDs.
- Unexpected candidate records.
- Missing candidates from the refinement stage.
- Refinement boundary conditions.

## Technology Stack

| Category | Technologies |
|---|---|
| Language | Python 3.13 |
| Numerical Computing | NumPy |
| Data Processing | Pandas |
| Orbital Mechanics | SGP4 |
| Data Storage | Parquet, JSON |
| Testing | Pytest |
| Containerization | Docker, Docker Compose |
| CI | GitHub Actions |
| Data Source | CelesTrak |

## Project Structure

```text
satellite-orbital-analytics/
│
├── src/
│   ├── data/
│   │   ├── fetch_celestrak.py
│   │   ├── fetch_candidate_satellites.py
│   │   ├── validate_candidate_satellites.py
│   │   └── clean_candidate_satellites.py
│   │
│   └── propagation/
│       ├── sgp4_propagator.py
│       ├── validate_propagation.py
│       ├── propagate_candidates.py
│       ├── find_close_approaches.py
│       ├── refine_close_approaches.py
│       └── validate_refined_approaches.py
│
├── scripts/
│   └── run_pipeline.sh
│
├── tests/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── Dockerfile
├── .dockerignore
├── compose.yaml
├── requirements.txt
└── README.md
```

## Installation

Clone the repository:

```bash
git clone https://github.com/ajaya-kumar-patel/satellite-orbital-analytics.git
cd satellite-orbital-analytics
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Pipeline

### Full Pipeline

Fetch fresh orbital data, validate and clean the catalog, and execute all analysis stages:

```bash
bash scripts/run_pipeline.sh --full
```

### Analysis Only

Use previously downloaded and cleaned orbital data:

```bash
bash scripts/run_pipeline.sh --analysis
```

The analysis mode requires:

- `data/raw/iss/iss_gp_snapshot.json`
- `data/processed/iss/clean_candidate_satellites.json`

## Docker

Build the Docker image:

```bash
docker build -t satellite-orbital-analytics:latest .
```

Run the pipeline usage command:

```bash
docker run --rm satellite-orbital-analytics:latest
```

Run the unit tests inside Docker:

```bash
docker run --rm satellite-orbital-analytics:latest python -m pytest -v
```

### Docker Compose

The Compose configuration mounts the local data directory into the container:

```yaml
volumes:
  - ./data:/app/data
```

This allows the container to read existing orbital datasets and persist generated results on the host machine.

Run the analysis pipeline:

```bash
docker compose run --rm satellite-analytics bash scripts/run_pipeline.sh --analysis
```

Run the full pipeline:

```bash
docker compose run --rm satellite-analytics bash scripts/run_pipeline.sh --full
```

## Testing and Continuous Integration

The project contains **44 unit tests** covering:

- Satellite catalog validation and cleaning.
- SGP4 propagation.
- Propagation output validation.
- Three-dimensional close-approach screening.
- Minimum-separation refinement.
- Refined dataset validation.

Run tests locally:

```bash
python -m pytest -v
```

GitHub Actions automatically:

1. Sets up Python 3.13.
2. Installs project dependencies.
3. Executes the Python unit tests.
4. Builds the Docker image.
5. Executes the same unit tests inside Docker.

The workflow runs on every push and pull request.

## Example Analysis Results

One successful analysis run processed:

| Metric | Result |
|---|---:|
| Candidate satellites propagated | 16,834 |
| Successful propagations | 16,834 |
| Position records generated | 4,865,026 |
| Broad screening threshold | 100 km |
| Screening records | 160 |
| Unique screened candidates | 152 |
| Refined candidates | 152 |
| Refinement failures | 0 |
| Refined data validation | Passed |

**Closest refined approach in this example run:**

| Parameter | Value |
|---|---|
| Object | STARLINK-30994 |
| NORAD ID | 58483 |
| Minimum estimated separation | 13.576 km |
| Relative velocity | 1.191 km/s |
| Estimated TCA | 2026-11-02 19:39:21 UTC |

These results are an example from a particular catalog snapshot and analysis window. They are not guaranteed to reproduce with newer orbital data.

## Limitations

- Results depend on the accuracy and age of catalog orbital elements.
- Broad screening uses discrete 5-minute position samples and can miss events between samples.
- Refinement is performed only for candidates identified by broad screening.
- The refinement window and sampling interval limit the temporal resolution of estimated minimum separation.
- The analysis is based on catalog-based SGP4 propagation and does not constitute an operational conjunction assessment.
- No operational collision probability or collision-avoidance decision is produced.

## Future Improvements

- Adaptive temporal sampling for close-approach screening.
- Improved candidate filtering and catalog freshness management.
- Historical conjunction analysis and trend monitoring.
- Enhanced visualization of orbital trajectories and close approaches.

## Author

**Ajaya Kumar Patel**

M.Tech, Cryptology & Security — Indian Statistical Institute, Kolkata

B.Tech, Aerospace Engineering — Indian Institute of Space Science and Technology

GitHub: [ajaya-kumar-patel](https://github.com/ajaya-kumar-patel)
