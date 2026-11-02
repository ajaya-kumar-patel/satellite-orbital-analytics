
#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="${PYTHON:-python}"
MODE="${1:---full}"

START_TIME=$SECONDS
CURRENT_STAGE="Initialization"

trap 'status=$?; echo ""; echo "ERROR: Pipeline failed during: ${CURRENT_STAGE}"; echo "Exit code: ${status}"; exit "$status"' ERR

run_stage() {
    CURRENT_STAGE="$1"
    shift

    echo ""
    echo "=================================================="
    echo "STAGE: ${CURRENT_STAGE}"
    echo "=================================================="

    local stage_start=$SECONDS
    "$@"
    echo "Completed: ${CURRENT_STAGE}"
    echo "Duration: $((SECONDS - stage_start)) seconds"
}

case "$MODE" in
    --full)
        echo "Running FULL pipeline..."

        run_stage "Fetch ISS orbital data" "$PYTHON" -m src.data.fetch_celestrak
        run_stage "Fetch candidate satellite catalog" "$PYTHON" -m src.data.fetch_candidate_satellites
        run_stage "Validate candidate satellite catalog" "$PYTHON" -m src.data.validate_candidate_satellites
        run_stage "Clean candidate satellite catalog" "$PYTHON" -m src.data.clean_candidate_satellites
        ;;
    --analysis)
        echo "Running ANALYSIS pipeline..."

        # Check that required input files exist
        for file in \
            data/processed/iss/clean_candidate_satellites.json \
            data/raw/iss/iss_gp_snapshot.json
        do
            if [[ ! -f "$file" ]]; then
                echo "ERROR: Required file missing: $file"
                echo "Run ./scripts/run_pipeline.sh --full first."
                exit 1
            fi
        done
        ;;
    *)
        echo "Usage: $0 [--full | --analysis]"
        exit 1
        ;;
esac

# Common orbital analysis stages
run_stage "Propagate ISS orbit" "$PYTHON" -m src.propagation.sgp4_propagator
run_stage "Validate ISS propagation" "$PYTHON" -m src.propagation.validate_propagation
run_stage "Propagate candidate satellites" "$PYTHON" -m src.propagation.propagate_candidates
run_stage "Broad close-approach screening" "$PYTHON" -m src.propagation.find_close_approaches
run_stage "Refine close approaches" "$PYTHON" -m src.propagation.refine_close_approaches
run_stage "Validate refined close approaches" "$PYTHON" -m src.propagation.validate_refined_approaches

echo ""
echo "Pipeline completed successfully."
echo "Total duration: $((SECONDS - START_TIME)) seconds"
