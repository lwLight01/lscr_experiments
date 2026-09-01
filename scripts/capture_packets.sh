#!/bin/bash

OUTPUT=${1:-"pcaps/capture.pcap"}
PORT=${2:-9002}

mkdir -p "$(dirname "$OUTPUT")"

echo "[capture] Starting tcpdump on lo, port $PORT → $OUTPUT"
sudo tcpdump -i lo -w "$OUTPUT" "udp port $PORT" &
echo $!
