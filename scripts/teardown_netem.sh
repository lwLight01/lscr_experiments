#!/bin/bash

IFACE="lo"

sudo tc qdisc del dev $IFACE root 2>/dev/null
echo "[teardown] All tc/netem rules cleared on $IFACE"
echo "Current state:"
sudo tc qdisc show dev $IFACE
