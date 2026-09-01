import struct

OFFSET_SID   = 0
OFFSET_EPOCH = 16
OFFSET_SN    = 18
OFFSET_NONCE = 22
OFFSET_CT    = 34

HEADER_SIZE  = 34

def pack_message(sid: bytes, epoch: int, sn: int, nonce: bytes,
                 ciphertext_with_tag: bytes) -> bytes:

    assert len(sid)   == 16, f"SID must be 16 bytes, got {len(sid)}"
    assert len(nonce) == 12, f"Nonce must be 12 bytes, got {len(nonce)}"

    header = struct.pack('>HI', epoch, sn)
    return sid + header + nonce + ciphertext_with_tag

def parse_message(packet: bytes) -> dict:

    if len(packet) < HEADER_SIZE:
        raise ValueError(f"Packet too short: {len(packet)} < {HEADER_SIZE} bytes")

    sid          = packet[OFFSET_SID   : OFFSET_EPOCH]
    epoch        = struct.unpack('>H', packet[OFFSET_EPOCH:OFFSET_SN])[0]
    sn           = struct.unpack('>I', packet[OFFSET_SN   :OFFSET_NONCE])[0]
    nonce        = packet[OFFSET_NONCE : OFFSET_CT]
    ct_with_tag  = packet[OFFSET_CT:]

    aad = packet[:OFFSET_NONCE]

    return {
        'sid':         sid,
        'epoch':       epoch,
        'sn':          sn,
        'nonce':       nonce,
        'ct_with_tag': ct_with_tag,
        'aad':         aad,
    }

def build_aad(sid: bytes, epoch: int, sn: int) -> bytes:

    return sid + struct.pack('>HI', epoch, sn)
