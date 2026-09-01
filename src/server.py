import argparse
import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from baseline import BaselineProtocol, SessionTerminated
from config import (
    CLIENT_PORT, SERVER_PORT, LOOPBACK,
    MESSAGES_PER_TRIAL, MESSAGE_RATE,
    INTERRUPTION_START_MSG, INTERRUPTION_DURATION,
)
from lscr import LSCRProtocol
from metrics import MetricsCollector
from state_manager import SessionState

def run_server(
    mode:        str = "baseline",
    num_messages: int = MESSAGES_PER_TRIAL,
    scenario:    str = "S1",
    trial:       int = 1,
    output_file: str = "results/server.csv",
    key_file:    str = "shared_key.bin",
):

    print(f"[server] Starting | mode={mode} | scenario={scenario} | trial={trial}")

    with open(key_file, 'rb') as f:
        shared_key = f.read()
    assert len(shared_key) == 32, "shared_key.bin must be exactly 32 bytes"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((LOOPBACK, SERVER_PORT))
    sock.settimeout(30.0)

    print("[server] Waiting for client SID...")
    try:
        sid_data, client_addr = sock.recvfrom(16)
    except socket.timeout:
        print("[server] Timeout waiting for SID — exiting")
        sock.close()
        return

    print(f"[server] Received SID from {client_addr}: {sid_data.hex()[:16]}…")

    state = SessionState(shared_key, sender_id=1)
    state.sid = sid_data

    protocol: BaselineProtocol | LSCRProtocol
    if mode == "lscr":
        protocol = LSCRProtocol()
    else:
        protocol = BaselineProtocol()
    protocol.init_session(state)

    metrics  = MetricsCollector(scenario=scenario, mode=mode, trial=trial)
    received = 0

    restart_scenarios  = {"S9"}
    do_restart         = (scenario in restart_scenarios)
    restarted          = False

    while received < num_messages:

        if do_restart and not restarted and received >= INTERRUPTION_START_MSG:
            print(f"[server] Simulating endpoint restart at msg {received}")
            state = SessionState(shared_key, sender_id=1)
            state.sid = sid_data
            protocol.init_session(state)
            metrics.record_session_failure("endpoint_restart")
            restarted = True

        try:
            data, addr = sock.recvfrom(65535)
            t_recv = time.perf_counter_ns()

        except socket.timeout:
            print(f"[server] Timeout — received {received}/{num_messages} messages")
            break

        try:
            plaintext = protocol.receive_message(state, data)

            if hasattr(protocol, 'has_pending_output'):
                while protocol.has_pending_output():
                    ctrl = protocol.pop_outbound()
                    if ctrl:
                        sock.sendto(ctrl, addr)

            if plaintext is not None:
                received += 1
                metrics.record_recv(received, t_recv, len(data), success=True)
            else:
                metrics.record_recv(received, t_recv, len(data),
                                    success=False, reason="auth_fail_or_replay")

        except SessionTerminated as e:
            print(f"[server] Session terminated at msg {received}: {e}")
            metrics.record_session_failure(str(e))

            try:
                sid_data, client_addr = sock.recvfrom(16)
                state = SessionState(shared_key, sender_id=1)
                state.sid = sid_data
                protocol.init_session(state)
                print(f"[server] Re-established session: {sid_data.hex()[:16]}…")
            except socket.timeout:
                print("[server] Timeout waiting for re-establishment")
                break

    print(f"[server] Done | received={received}/{num_messages} messages")
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    metrics.save(output_file)
    sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LSCR Experiment — UDP Server")
    parser.add_argument('--mode',     choices=['baseline', 'lscr'], default='baseline',
                        help="Protocol mode")
    parser.add_argument('--messages', type=int, default=MESSAGES_PER_TRIAL,
                        help="Number of messages to receive")
    parser.add_argument('--scenario', default='S1',
                        help="Scenario ID (S1–S12)")
    parser.add_argument('--trial',    type=int, default=1,
                        help="Trial number")
    parser.add_argument('--output',   default='results/server.csv',
                        help="Output CSV path")
    parser.add_argument('--key',      default='shared_key.bin',
                        help="Path to shared key file")
    args = parser.parse_args()

    run_server(
        mode        = args.mode,
        num_messages= args.messages,
        scenario    = args.scenario,
        trial       = args.trial,
        output_file = args.output,
        key_file    = args.key,
    )
