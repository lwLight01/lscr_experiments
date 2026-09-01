import os
import time

from replay_window import ReplayWindow

class SessionState:

    def __init__(self, session_key: bytes, sender_id: int):
        assert len(session_key) == 32, "Session key must be 256 bits (32 bytes)"
        assert sender_id in (0, 1), "sender_id must be 0 (client) or 1 (server)"

        self.sid              = os.urandom(16)
        self.sk               = session_key
        self.nc               = 0
        self.sn_send          = 0
        self.sn_recv          = 0
        self.epoch            = 0
        self.sender_id        = sender_id

        self.replay_window    = ReplayWindow(64)

        self.state_digest     = b'\x00' * 32
        self.t_last           = time.time()

        self.f_count          = 0
        self.suspicious_count = 0

    def reset_for_recovery(self):

        self.f_count          = 0
        self.suspicious_count = 0
        self.replay_window.reset()

    def zeroize(self):

        self.sk               = b'\x00' * 32
        self.nc               = 0
        self.sn_send          = 0
        self.sn_recv          = 0
        self.f_count          = 0
        self.suspicious_count = 0
        self.epoch            = 0
        self.replay_window.reset()
        self.state_digest     = b'\x00' * 32

    def __repr__(self):
        return (
            f"SessionState("
            f"sid={self.sid.hex()[:8]}…, "
            f"epoch={self.epoch}, "
            f"sn_send={self.sn_send}, "
            f"sn_recv={self.sn_recv}, "
            f"nc={self.nc}, "
            f"f_count={self.f_count})"
        )
