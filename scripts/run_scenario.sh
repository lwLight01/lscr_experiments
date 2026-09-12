#!/bin/bash

SCENARIO=${1:-"S1"}
MODE=${2:-"baseline"}
TRIAL=${3:-1}
PROJ_DIR="$HOME/lscr-experiment"
SRC="$PROJ_DIR/src"
RESULTS="$PROJ_DIR/results"
LOGS="$PROJ_DIR/logs"
PCAPS="$PROJ_DIR/pcaps"

if [[ ! "$SCENARIO" =~ ^S([1-9]|1[0-2])$ ]]; then
    echo "[ERROR] Invalid scenario: $SCENARIO. Must be S1–S12."
    exit 1
fi
if [[ "$MODE" != "baseline" && "$MODE" != "lscr" ]]; then
    echo "[ERROR] Invalid mode: $MODE. Must be 'baseline' or 'lscr'."
    exit 1
fi

echo " Scenario: $SCENARIO | Mode: $MODE | Trial: $TRIAL"

source "$PROJ_DIR/venv/bin/activate"

mkdir -p "$RESULTS" "$LOGS" "$PCAPS"

"$PROJ_DIR/scripts/setup_netem.sh" "$SCENARIO"

PCAP_FILE="$PCAPS/${SCENARIO}_${MODE}_t${TRIAL}.pcap"
sudo tcpdump -i lo -w "$PCAP_FILE" udp port 9002 &>/dev/null &
TCPDUMP_PID=$!
sleep 0.5

SERVER_CSV="$RESULTS/${SCENARIO}_${MODE}_t${TRIAL}_server.csv"
python3 "$SRC/server.py" \
    --mode     "$MODE" \
    --messages 1000 \
    --scenario "$SCENARIO" \
    --trial    "$TRIAL" \
    --output   "$SERVER_CSV" \
    --key      "$PROJ_DIR/shared_key.bin" \
    > "$LOGS/${SCENARIO}_${MODE}_t${TRIAL}_server.log" 2>&1 &
SERVER_PID=$!
echo "[run] Server PID: $SERVER_PID"
sleep 1

CLIENT_CSV="$RESULTS/${SCENARIO}_${MODE}_t${TRIAL}_client.csv"
python3 "$SRC/client.py" \
    --mode     "$MODE" \
    --messages 1000 \
    --rate     100 \
    --scenario "$SCENARIO" \
    --trial    "$TRIAL" \
    --output   "$CLIENT_CSV" \
    --key      "$PROJ_DIR/shared_key.bin" \
    > "$LOGS/${SCENARIO}_${MODE}_t${TRIAL}_client.log" 2>&1
echo "[run] Client finished"

wait $SERVER_PID
echo "Server finished"

sudo kill $TCPDUMP_PID 2>/dev/null
wait $TCPDUMP_PID 2>/dev/null
echo "Packet capture saved → $PCAP_FILE"

"$PROJ_DIR/scripts/teardown_netem.sh"

if [ "$SCENARIO" = "S10" ]; then
    echo "[run] Running replay attacker for S10..."
    sudo python3 "$SRC/replay_attacker.py" \
        --target-port      9002 \
        --capture-duration 5 \
        --replay-delay     1 \
        --replay-count     50 \
        --iface            lo \
        >> "$LOGS/${SCENARIO}_${MODE}_t${TRIAL}_attacker.log" 2>&1
fi

echo ""
echo "Trial $TRIAL complete for $SCENARIO ($MODE)"
echo "Results: $SERVER_CSV"
echo "$CLIENT_CSV"
