#!/bin/bash

PROJ_DIR="$HOME/lscr-experiment"

SCENARIOS="S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12"
MODES="baseline lscr"
TRIALS=10

TOTAL=$((12 * 2 * TRIALS))
COUNT=0
FAILED=0

echo "========================================================"
echo " LSCR Experiment — Full Run"
echo " Scenarios: 12 | Modes: 2 | Trials per: $TRIALS"
echo " Total experiments: $TOTAL"
echo " Estimated time: ~2–4 hours"
echo " Started: $(date)"
echo "========================================================"

START_TIME=$(date +%s)

for scenario in $SCENARIOS; do
    for mode in $MODES; do
        for trial in $(seq 1 $TRIALS); do
            COUNT=$((COUNT + 1))

            echo ""
            echo "--- [$COUNT/$TOTAL] $scenario | $mode | Trial $trial / $TRIALS ---"

            if sudo "$PROJ_DIR/scripts/run_scenario.sh" "$scenario" "$mode" "$trial"; then
                echo "[run_all] ✓ OK"
            else
                echo "[run_all] ✗ FAILED — $scenario $mode trial $trial"
                FAILED=$((FAILED + 1))
                echo "$scenario,$mode,$trial,FAILED" >> "$PROJ_DIR/logs/failed_trials.csv"
            fi

            sleep 2
        done
    done
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))

echo ""
echo "========================================================"
echo " ALL EXPERIMENTS COMPLETE"
echo " Finished: $(date)"
echo " Total time: ${MINUTES} minutes"
echo " Succeeded: $((TOTAL - FAILED)) / $TOTAL"
echo " Failed:    $FAILED / $TOTAL"
if [ $FAILED -gt 0 ]; then
    echo " Failed trials logged to: $PROJ_DIR/logs/failed_trials.csv"
fi
echo "========================================================"
echo ""
echo "Next step: cd $PROJ_DIR/analysis && python3 analyze.py"
