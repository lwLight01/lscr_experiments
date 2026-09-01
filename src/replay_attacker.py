import argparse
import sys
import time

try:
    from scapy.all import sniff, sendp
except ImportError:
    print("[ERROR] scapy is not installed. Run: pip install scapy")
    sys.exit(1)

class ReplayAttacker:

    def __init__(self, target_port: int = 9002,
                 replay_delay: float = 1.0,
                 replay_count: int   = 10):
        self.target_port  = target_port
        self.replay_delay = replay_delay
        self.replay_count = replay_count
        self.captured     = []
        self.replayed     = 0

    def start_capture(self, duration: float = 5.0, iface: str = "lo"):

        print(f"[attacker] Capturing on {iface} for {duration}s "
              f"(port {self.target_port})...")
        packets = sniff(
            filter  = f"udp and port {self.target_port}",
            timeout = duration,
            iface   = iface,
        )
        self.captured = list(packets)
        print(f"[attacker] Captured {len(self.captured)} packets")

    def replay(self, iface: str = "lo") -> int:

        if not self.captured:
            print("[attacker] No packets to replay")
            return 0

        print(f"[attacker] Waiting {self.replay_delay}s before replay...")
        time.sleep(self.replay_delay)

        to_replay = self.captured[:self.replay_count]
        print(f"[attacker] Replaying {len(to_replay)} packets...")

        for pkt in to_replay:
            sendp(pkt, iface=iface, verbose=False)
            self.replayed += 1

        print(f"[attacker] Done — replayed {self.replayed} packets")
        print("[attacker] Expected: ALL replayed packets rejected by anti-replay window")
        return self.replayed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LSCR Replay Attacker — Scenario S10"
    )
    parser.add_argument('--target-port',      type=int,   default=9002,
                        help="UDP port to attack")
    parser.add_argument('--capture-duration', type=float, default=5.0,
                        help="Seconds to capture packets")
    parser.add_argument('--replay-delay',     type=float, default=1.0,
                        help="Seconds to wait before replaying")
    parser.add_argument('--replay-count',     type=int,   default=10,
                        help="Number of packets to replay")
    parser.add_argument('--iface',            default='lo',
                        help="Network interface (default: lo)")
    args = parser.parse_args()

    attacker = ReplayAttacker(
        target_port  = args.target_port,
        replay_delay = args.replay_delay,
        replay_count = args.replay_count,
    )
    attacker.start_capture(args.capture_duration, args.iface)
    attacker.replay(args.iface)
