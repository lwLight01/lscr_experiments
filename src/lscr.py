import os
import struct
import time
from enum import Enum

from baseline import SessionTerminated
from config import (
    MSG_DATA, MSG_STATE_CHECK, MSG_SYNC_REQ, MSG_SYNC_RESP, MSG_SYNC_CONFIRM,
    MAX_EPOCH_DRIFT, MAX_SN_DRIFT, MAX_RECOVERY_GAP, MAX_NC_RECOVERY_GAP,
    THETA_F, STATE_CHECK_PERIOD, SUSPICIOUS_THRESHOLD, WINDOW_SIZE,
)
from crypto_engine import CryptoEngine
from message import pack_message, parse_message, build_aad
from state_manager import SessionState

class DivergenceType(Enum):
    RECOVERABLE_MINOR  = "RECOVERABLE_MINOR"
    RECOVERABLE_MAJOR  = "RECOVERABLE_MAJOR"
    STALE              = "STALE"
    SUSPICIOUS         = "SUSPICIOUS"
    IRRECOVERABLE      = "IRRECOVERABLE"
    UNKNOWN            = "UNKNOWN"

def classify_divergence(state: SessionState,
                        remote_sid: bytes,
                        remote_epoch: int,
                        remote_sn: int) -> DivergenceType:

    if remote_sid != state.sid:
        return DivergenceType.IRRECOVERABLE

    epoch_diff = remote_epoch - state.epoch
    if abs(epoch_diff) > MAX_EPOCH_DRIFT:
        return DivergenceType.IRRECOVERABLE

    sn_diff = remote_sn - state.sn_recv

    if sn_diff < -WINDOW_SIZE:

        return DivergenceType.STALE

    elif sn_diff > MAX_SN_DRIFT:

        return DivergenceType.SUSPICIOUS

    elif 0 <= sn_diff <= WINDOW_SIZE:

        return DivergenceType.RECOVERABLE_MINOR

    elif WINDOW_SIZE < sn_diff <= MAX_SN_DRIFT:

        return DivergenceType.RECOVERABLE_MAJOR

    return DivergenceType.UNKNOWN

class LSCRProtocol:

    def __init__(self):
        self.crypto             = CryptoEngine()
        self.pending_challenge  = None
        self._outbound_queue    = []

    def init_session(self, state: SessionState):

        self.crypto.set_key(state.sk)

    def has_pending_output(self) -> bool:

        return len(self._outbound_queue) > 0

    def pop_outbound(self) -> bytes | None:

        if self._outbound_queue:
            return self._outbound_queue.pop(0)
        return None

    def send_message(self, state: SessionState, plaintext: bytes) -> bytes:

        state.sn_send += 1
        state.nc      += 1

        nonce = CryptoEngine.construct_nonce(state.epoch, state.sender_id, state.nc)
        aad   = build_aad(state.sid, state.epoch, state.sn_send)

        include_digest = (state.sn_send % STATE_CHECK_PERIOD == 0)

        if include_digest:
            sd = CryptoEngine.compute_state_digest(
                state.sk, state.sid, state.epoch,
                state.sn_send, state.sn_recv, state.nc,
            )
            payload = bytes([MSG_STATE_CHECK]) + sd + plaintext
        else:
            payload = bytes([MSG_DATA]) + plaintext

        ct_with_tag = self.crypto.encrypt(nonce, payload, aad)
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

        if epoch != state.epoch:
            classification = classify_divergence(state, sid, epoch, sn)
            self._handle_divergence(classification, state)
            return None

        payload = self.crypto.decrypt(nonce, ct_with_tag, aad)

        if payload is None:
            state.f_count += 1
            if state.f_count > THETA_F:
                self._trigger_state_check(state)
            return None

        if not state.replay_window.check_and_update(sn):
            return None

        state.sn_recv = max(state.sn_recv, sn)
        state.f_count = 0
        state.t_last  = time.time()

        msg_type = payload[0]
        body     = payload[1:]

        if msg_type == MSG_DATA:
            return body

        elif msg_type == MSG_STATE_CHECK:

            sd_remote = body[:32]
            plaintext  = body[32:]
            self._verify_state_digest(state, sid, epoch, sn, sd_remote)
            return plaintext

        elif msg_type == MSG_SYNC_REQ:
            self._handle_sync_request(state, body)
            return None

        elif msg_type == MSG_SYNC_RESP:
            self._handle_sync_response(state, body)
            return None

        elif msg_type == MSG_SYNC_CONFIRM:
            self._handle_sync_confirm(state, body)
            return None

        return None

    def _handle_divergence(self, classification: DivergenceType,
                            state: SessionState):

        if classification == DivergenceType.RECOVERABLE_MINOR:
            self._minor_recovery(state)

        elif classification == DivergenceType.RECOVERABLE_MAJOR:
            self._major_recovery(state)

        elif classification == DivergenceType.STALE:
            pass

        elif classification == DivergenceType.SUSPICIOUS:
            state.suspicious_count += 1
            if state.suspicious_count > SUSPICIOUS_THRESHOLD:
                self._secure_fallback(state)
            else:
                self._trigger_state_check(state)

        else:
            self._secure_fallback(state)

    def _verify_state_digest(self, state: SessionState, sid: bytes,
                              epoch: int, sn: int, sd_remote: bytes):

        sd_local = CryptoEngine.compute_state_digest(
            state.sk, state.sid, state.epoch,
            state.sn_send, state.sn_recv, state.nc,
        )
        if sd_remote != sd_local:
            classification = classify_divergence(state, sid, epoch, sn)
            self._handle_divergence(classification, state)

    def _minor_recovery(self, state: SessionState):

        pass

    def _major_recovery(self, state: SessionState):

        nonce_challenge         = os.urandom(16)
        self.pending_challenge  = nonce_challenge

        sd = CryptoEngine.compute_state_digest(
            state.sk, state.sid, state.epoch,
            state.sn_send, state.sn_recv, state.nc,
        )
        sync_body = (
            sd
            + struct.pack('>IIQ', state.sn_send, state.sn_recv, state.nc)
            + nonce_challenge
        )

        packet = self._build_control_packet(state, MSG_SYNC_REQ, sync_body)
        if packet:
            self._outbound_queue.append(packet)

    def _handle_sync_request(self, state: SessionState, body: bytes):

        if len(body) < 64:
            return

        sd_remote        = body[:32]
        sn_send_remote   = struct.unpack('>I', body[32:36])[0]
        sn_recv_remote   = struct.unpack('>I', body[36:40])[0]
        nc_remote        = struct.unpack('>Q', body[40:48])[0]
        nonce_challenge  = body[48:64]

        delta_sn = sn_send_remote - state.sn_recv
        delta_nc = nc_remote      - state.nc

        safe = (
            0 <= delta_sn <= MAX_RECOVERY_GAP
            and 0 <= delta_nc <= MAX_NC_RECOVERY_GAP
        )

        nonce_response = CryptoEngine.compute_hmac(
            state.sk, nonce_challenge + b"sync_ack"
        )

        if safe:
            decision = b'\x01'

            state.sn_recv        = max(state.sn_recv, sn_recv_remote)
            state.nc             = max(state.nc, nc_remote)
            state.replay_window.reset()
        else:
            decision = b'\x00'

        resp_body = decision + nonce_response
        packet = self._build_control_packet(state, MSG_SYNC_RESP, resp_body)
        if packet:
            self._outbound_queue.append(packet)

    def _handle_sync_response(self, state: SessionState, body: bytes):

        if len(body) < 33 or self.pending_challenge is None:
            return

        decision        = body[0]
        nonce_response  = body[1:33]

        expected = CryptoEngine.compute_hmac(
            state.sk, self.pending_challenge + b"sync_ack"
        )
        self.pending_challenge = None

        if decision == 0x01 and nonce_response == expected:

            state.epoch            += 1
            state.f_count           = 0
            state.suspicious_count  = 0
            state.replay_window.reset()
            confirm_body = b'\x01'
        else:
            confirm_body = b'\x00'

        packet = self._build_control_packet(state, MSG_SYNC_CONFIRM, confirm_body)
        if packet:
            self._outbound_queue.append(packet)

    def _handle_sync_confirm(self, state: SessionState, body: bytes):

        if not body:
            return
        if body[0] == 0x01:

            state.f_count           = 0
            state.suspicious_count  = 0

    def _trigger_state_check(self, state: SessionState):

        sd = CryptoEngine.compute_state_digest(
            state.sk, state.sid, state.epoch,
            state.sn_send, state.sn_recv, state.nc,
        )
        state.state_digest = sd

        packet = self._build_control_packet(state, MSG_STATE_CHECK, sd + b"")
        if packet:
            self._outbound_queue.append(packet)

    def _secure_fallback(self, state: SessionState):

        state.zeroize()
        raise SessionTerminated("Irrecoverable divergence — session zeroized, re-establish required")

    def _build_control_packet(self, state: SessionState,
                               msg_type: int, body: bytes) -> bytes | None:

        try:
            state.sn_send += 1
            state.nc      += 1
            nonce  = CryptoEngine.construct_nonce(state.epoch, state.sender_id, state.nc)
            aad    = build_aad(state.sid, state.epoch, state.sn_send)
            payload = bytes([msg_type]) + body
            ct_with_tag = self.crypto.encrypt(nonce, payload, aad)
            return pack_message(state.sid, state.epoch, state.sn_send,
                                nonce, ct_with_tag)
        except Exception:
            return None
