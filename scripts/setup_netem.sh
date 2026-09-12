#!/bin/bash

SCENARIO=$1
IFACE="lo"

if [ -z "$SCENARIO" ]; then
    echo "Usage: $0 {S1|S2|S3|S4|S5|S6|S7|S8|S9|S10|S11|S12}"
    exit 1
fi

sudo tc qdisc del dev $IFACE root 2>/dev/null

echo " Applying tc/netem for: $SCENARIO on $IFACE"

case $SCENARIO in
    S1)
        echo "[S1] Normal — no network impairment"
        ;;
    S2)
        echo "[S2] 1% random packet loss"
        sudo tc qdisc add dev $IFACE root netem loss 1%
        ;;
    S3)
        echo "[S3] 5% random packet loss"
        sudo tc qdisc add dev $IFACE root netem loss 5%
        ;;
    S4)
        echo "[S4] 10% random packet loss"
        sudo tc qdisc add dev $IFACE root netem loss 10%
        ;;
    S5)
        echo "[S5] 5% packet duplication"
        sudo tc qdisc add dev $IFACE root netem duplicate 5%
        ;;
    S6)
        echo "[S6] 25% packet reordering (10ms base delay, gap 5)"
        sudo tc qdisc add dev $IFACE root netem delay 10ms reorder 25% gap 5
        ;;
    S7)
        echo "[S7] 50ms delay +/- 20ms jitter (normal distribution)"
        sudo tc qdisc add dev $IFACE root netem delay 50ms 20ms distribution normal
        ;;
    S8)
        echo "[S8] Connection interruption — handled programmatically in client.py"
        echo "     (client sleeps for INTERRUPTION_DURATION at INTERRUPTION_START_MSG)"
        ;;
    S9)
        echo "[S9] Endpoint restart — handled programmatically in server.py"
        echo "     (server resets state mid-trial at INTERRUPTION_START_MSG)"
        ;;
    S10)
        echo "[S10] Replay attack — handled by replay_attacker.py"
        echo "      (run: sudo python3 src/replay_attacker.py after starting session)"
        ;;
    S11)
        echo "[S11] Combined: 5% loss + 25% reordering"
        sudo tc qdisc add dev $IFACE root netem loss 5% delay 10ms reorder 25% gap 5
        ;;
    S12)
        echo "[S12] Combined: 5% loss + connection interruption"
        sudo tc qdisc add dev $IFACE root netem loss 5%
        echo "      (interruption is handled programmatically in client.py)"
        ;;
    *)
        echo "[ERROR] Unknown scenario: $SCENARIO"
        echo "Usage: $0 {S1|S2|S3|S4|S5|S6|S7|S8|S9|S10|S11|S12}"
        exit 1
        ;;
esac

echo ""
echo "Current tc/netem rules on $IFACE:"
sudo tc qdisc show dev $IFACE
