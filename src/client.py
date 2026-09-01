import argparse
import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from baseline import BaselineProtocol, SessionTerminated
from config import (
    CLIENT_PORT, SERVER_PORT, LOOPBACK, SERVER_ADDR,
    MESSAGES_PER_TRIAL, MESSAGE_RATE,
    INTERRUPTION_START_MSG, INTERRUPTION_DURATION,
)
from lscr import LSCRProtocol
from metrics import MetricsCollector
from state_manager import SessionState

def run_client(
    mode:        str = "baseline",
    num_messages: int = MESSAGES_PER_TRIAL,
    rate:        int = MESSAGE_RATE,
    scenario:    str = "S1",
    trial:       int = 1,
    output_file: str = "results/client.csv",
    key_file:    str = "shared_key.bin",
):

    print(f"[client] Starting | mode={mode} | scenario={scenario} | trial={trial}")

    with open(key_file, 'rb') as f:
        shared_key = f.read()
    assert len(shared_key) == 32, "shared_key.bin must be exactly 32 bytes"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LOOPBACK, CLIENT_PORT))

    state = SessionState(shared_key, sender_id=0)

    server_addr = (SERVER_ADDR, SERVER_PORT)
    sock.sendto(state.sid, server_addr)
    time.sleep(0.2)

    protocol: BaselineProtocol | LSCRProtocol
    if mode == "lscr":
        protocol = LSCRProtocol()
    else:
        protocol = BaselineProtocol()
    protocol.init_session(state)

    metrics  = MetricsCollector(scenario=scenario, mode=mode, trial=trial)
    interval = 1.0 / rate
    sent     = 0

    interruption_scenarios = {"S8", "S12"}
    do_interrupt = (scenario in interruption_scenarios)

    for i in range(num_messages):

        if do_interrupt and i == INTERRUPTION_START_MSG:
            print(f"[client] Simulating {INTERRUPTION_DURATION}s interruption at msg {i}")
            time.sleep(INTERRUPTION_DURATION)

        plaintext = f"MSG:{scenario}:{mode}:{i:06d}".encode()
        t_start   = time.perf_counter_ns()

        try:
            packet = protocol.send_message(state, plaintext)
        except SessionTerminated as e:
            print(f"[client] Session terminated at msg {i}: {e}")
            metrics.record_session_failure(str(e))

            state = SessionState(shared_key, sender_id=0)
            sock.sendto(state.sid, server_addr)
            time.sleep(0.2)
            protocol.init_session(state)
            continue

        sock.sendto(packet, server_addr)

        if hasattr(protocol, 'has_pending_output'):
            while protocol.has_pending_output():
                ctrl = protocol.pop_outbound()
                if ctrl:
                    sock.sendto(ctrl, server_addr)

        t_end = time.perf_counter_ns()
        sent += 1
        metrics.record_send(i, t_start, t_end, len(packet))

        nonce = packet[22:34]
        metrics.check_nonce_reuse(nonce)

        elapsed = (t_end - t_start) / 1e9
        if elapsed < interval:
            time.sleep(interval - elapsed)

    print(f"[client] Done | sent={sent}/{num_messages} messages")
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    metrics.save(output_file)
    sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LSCR Experiment — UDP Client")
    parser.add_argument('--mode',     choices=['baseline', 'lscr'], default='baseline',
                        help="Protocol mode")
    parser.add_argument('--messages', type=int,   default=MESSAGES_PER_TRIAL,
                        help="Number of messages to send")
    parser.add_argument('--rate',     type=int,   default=MESSAGE_RATE,
                        help="Target messages per second")
    parser.add_argument('--scenario', default='S1',
                        help="Scenario ID (S1–S12)")
    parser.add_argument('--trial',    type=int,   default=1,
                        help="Trial number")
    parser.add_argument('--output',   default='results/client.csv',
                        help="Output CSV path")
    parser.add_argument('--key',      default='shared_key.bin',
                        help="Path to shared key file")
    args = parser.parse_args()

    run_client(
        mode        = args.mode,
        num_messages= args.messages,
        rate        = args.rate,
        scenario    = args.scenario,
        trial       = args.trial,
        output_file = args.output,
        key_file    = args.key,
    )
