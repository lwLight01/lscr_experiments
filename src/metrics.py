import csv
import json
import time

import psutil

class MetricsCollector:

    def __init__(self, scenario: str = "S1", mode: str = "baseline", trial: int = 1):
        self.scenario   = scenario
        self.mode       = mode
        self.trial      = trial
        self.records    = []
        self.start_time = time.perf_counter_ns()
        self.process    = psutil.Process()

        self.nonce_set            = set()
        self.nonce_reuse_count    = 0
        self.replay_accepted      = 0
        self.invalid_accepted     = 0
        self.divergence_detected  = 0
        self.divergence_actual    = 0
        self.false_recoveries     = 0
        self.unsafe_recoveries    = 0

        self.recovery_attempts    = 0
        self.recovery_successes   = 0
        self.session_failures     = 0

        self.recovery_latencies   = []

    def record_send(self, msg_id: int, t_start: int, t_end: int,
                    packet_size: int):

        self.records.append({
            'msg_id':       msg_id,
            'direction':    'send',
            'timestamp_ns': t_start,
            'latency_ns':   t_end - t_start,
            'packet_size':  packet_size,
            'success':      True,
            'reason':       '',
            'cpu_percent':  self.process.cpu_percent(),
            'memory_bytes': self.process.memory_info().rss,
        })

    def record_recv(self, msg_id: int, t_recv: int, packet_size: int,
                    success: bool, reason: str = ""):

        self.records.append({
            'msg_id':       msg_id,
            'direction':    'recv',
            'timestamp_ns': t_recv,
            'latency_ns':   0,
            'packet_size':  packet_size,
            'success':      success,
            'reason':       reason,
            'cpu_percent':  self.process.cpu_percent(),
            'memory_bytes': self.process.memory_info().rss,
        })

    def record_session_failure(self, reason: str = ""):

        self.session_failures += 1

    def record_recovery(self, success: bool, latency_ms: float):

        self.recovery_attempts += 1
        if success:
            self.recovery_successes += 1
        self.recovery_latencies.append(latency_ms)

    def check_nonce_reuse(self, nonce: bytes) -> bool:

        if nonce in self.nonce_set:
            self.nonce_reuse_count += 1
            return True
        self.nonce_set.add(nonce)
        return False

    def save(self, filepath: str):

        if self.records:
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.records[0].keys())
                writer.writeheader()
                writer.writerows(self.records)

        summary_path = filepath.replace('.csv', '_summary.json')
        with open(summary_path, 'w') as f:
            json.dump(self.summary(), f, indent=2)

        print(f"[metrics] Saved {len(self.records)} records → {filepath}")
        print(f"[metrics] Summary → {summary_path}")

    def summary(self) -> dict:

        total_sent       = sum(1 for r in self.records if r.get('direction') == 'send')
        total_recv_ok    = sum(1 for r in self.records
                               if r.get('direction') == 'recv' and r.get('success'))
        total_recv_fail  = sum(1 for r in self.records
                               if r.get('direction') == 'recv' and not r.get('success'))

        send_latencies   = [r['latency_ns'] for r in self.records
                            if r.get('direction') == 'send']
        avg_lat_us = (sum(send_latencies) / len(send_latencies) / 1000.0
                      if send_latencies else 0.0)

        return {
            'scenario':                self.scenario,
            'mode':                    self.mode,
            'trial':                   self.trial,
            'total_sent':              total_sent,
            'total_received_ok':       total_recv_ok,
            'total_received_fail':     total_recv_fail,
            'avg_encrypt_latency_us':  round(avg_lat_us, 3),
            'nonce_reuse_count':       self.nonce_reuse_count,
            'replay_accepted':         self.replay_accepted,
            'invalid_accepted':        self.invalid_accepted,
            'divergence_detected':     self.divergence_detected,
            'divergence_actual':       self.divergence_actual,
            'recovery_attempts':       self.recovery_attempts,
            'recovery_successes':      self.recovery_successes,
            'session_failures':        self.session_failures,
            'unsafe_recoveries':       self.unsafe_recoveries,
            'false_recoveries':        self.false_recoveries,
            'avg_recovery_latency_ms': round(
                sum(self.recovery_latencies) / len(self.recovery_latencies), 3
            ) if self.recovery_latencies else 0.0,
            'detection_rate': round(
                self.divergence_detected / self.divergence_actual, 4
            ) if self.divergence_actual > 0 else 1.0,
            'recovery_success_rate': round(
                self.recovery_successes / self.recovery_attempts, 4
            ) if self.recovery_attempts > 0 else 1.0,
        }
