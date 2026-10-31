"""ISO-TP (ISO 15765-2) 프레이밍 (Phase 7).

UDS 페이로드를 CAN 8바이트 프레임들로 나누거나(송신),
받아서 재조립한다(수신). 원본 BUSMASTER `UDS_Protocol`의
`getFrameType` 등이 다루던 영역을 표준 기반으로 정리.

프레임 타입 (첫 바이트 상위 니블):
- 0x0: Single Frame (SF) — 하위 니블 = 데이터 길이 (CAN FD면 2바이트 길이)
- 0x1: First Frame (FF) — 하위 12비트 = 전체 길이
- 0x2: Consecutive Frame (CF) — 하위 니블 = 시퀀스 번호
- 0x3: Flow Control (FC) — CTS(0)/WAIT(1)/OVERFLOW(2), BlockSize, STmin
"""

from __future__ import annotations

from dataclasses import dataclass

SF, FF, CF, FC = 0x0, 0x1, 0x2, 0x3
FC_CTS, FC_WAIT, FC_OVERFLOW = 0, 1, 2
MAX_SF_LEN = 7  # 클래식 CAN Single Frame 최대 페이로드


@dataclass(frozen=True)
class FlowControl:
    """플로우 컨트롤 프레임 내용."""

    fs: int  # 0=CTS, 1=WAIT, 2=OVERFLOW
    block_size: int = 0
    st_min: int = 0

    def encode(self) -> bytes:
        return bytes([0x30 | (self.fs & 0xF), self.block_size & 0xFF,
                      self.st_min & 0xFF] + [0] * 5)

    @classmethod
    def decode(cls, frame: bytes) -> "FlowControl":
        if len(frame) < 3 or (frame[0] >> 4) != FC:
            raise ValueError("Flow Control 프레임이 아닙니다")
        return cls(fs=frame[0] & 0xF, block_size=frame[1], st_min=frame[2])


def encode(payload: bytes) -> list[bytes]:
    """UDS 페이로드 → CAN 프레임(8바이트) 리스트."""
    if len(payload) <= MAX_SF_LEN:
        return [bytes([len(payload)]) + payload.ljust(MAX_SF_LEN, b"\x00")]
    total = len(payload)
    if total > 0xFFF:
        raise ValueError("ISO-TP 페이로드가 너무 깁니다 (최대 4095)")
    frames = [bytes([0x10 | ((total >> 8) & 0xF), total & 0xFF])
              + payload[:6]]
    seq = 1
    rest = payload[6:]
    while rest:
        chunk, rest = rest[:7], rest[7:]
        frames.append(bytes([0x20 | (seq & 0xF)]) + chunk.ljust(7, b"\x00"))
        seq = (seq + 1) & 0xF
    return frames


def decode(frames: list[bytes]) -> bytes:
    """CAN 프레임 리스트 → 재조립된 UDS 페이로드."""
    if not frames:
        raise ValueError("프레임이 없습니다")
    first = frames[0][0] >> 4
    if first == SF:
        length = frames[0][0] & 0xF
        return bytes(frames[0][1:1 + length])
    if first != FF:
        raise ValueError("First Frame으로 시작하지 않았습니다")
    total = ((frames[0][0] & 0xF) << 8) | frames[0][1]
    data = bytearray(frames[0][2:8])
    seq = 1
    for frame in frames[1:]:
        if (frame[0] >> 4) != CF:
            raise ValueError("Consecutive Frame이 아닙니다")
        if (frame[0] & 0xF) != seq:
            raise ValueError(f"시퀀스 번호 불일치: 기대 {seq:#x}")
        data += frame[1:8]
        seq = (seq + 1) & 0xF
        if len(data) >= total:
            break
    return bytes(data[:total])


def frame_type(first_byte: int) -> str:
    """첫 바이트 → 프레임 타입 이름 (원본 `getFrameType` 대응)."""
    return {SF: "SingleFrame", FF: "FirstFrame",
            CF: "ConsecutiveFrame", FC: "FlowControl"}.get(
                first_byte >> 4, "Unknown")
