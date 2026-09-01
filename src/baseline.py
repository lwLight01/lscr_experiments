import struct
import time

from crypto_engine import CryptoEngine
from message import pack_message, parse_message, build_aad
from state_manager import SessionState

class SessionTerminated(Exception):

    pass

class BaselineProtocol:

    MAX_CONSECUTIVE_FAILURES = 5

    def __init__(self):
        self.crypto = CryptoEngine()

    def init_session(self, state: SessionState):

        self.crypto.set_key(state.sk)

    def send_message(self, state: SessionState, plaintext: bytes) -> bytes:

        state.sn_send += 1
        state.nc      += 1

        nonce = CryptoEngine.construct_nonce(state.epoch, state.sender_id, state.nc)
        aad   = build_aad(state.sid, state.epoch, state.sn_send)

        ct_with_tag = self.crypto.encrypt(nonce, plaintext, aad)
        packet      = pack_message(state.sid, state.epoch, state.sn_send,
                                   nonce, ct_with_tag)
        return packet

    def receive_message(self, state: SessionState, packet: bytes) -> bytes | None:

        try:
            fields = parse_message(packet)
        except ValueError:
            return None

        sid         = fields['sid']
        epoch       = fields['epoch']
        sn          = fields['sn']
        nonce       = fields['nonce']
        ct_with_tag = fields['ct_with_tag']
        aad         = fields['aad']

        if sid != state.sid:
            return None

        plaintext = self.crypto.decrypt(nonce, ct_with_tag, aad)

        if plaintext is None:

            state.f_count += 1
            if state.f_count > self.MAX_CONSECUTIVE_FAILURES:
                raise SessionTerminated(
                    f"Too many consecutive auth failures ({state.f_count})"
                )
            return None

        if not state.replay_window.check_and_update(sn):
            return None

        state.sn_recv = max(state.sn_recv, sn)
        state.f_count = 0
        state.t_last  = time.time()

        return plaintext
