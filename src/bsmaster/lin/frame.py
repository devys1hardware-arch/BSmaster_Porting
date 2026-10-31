"""LIN 프레임 자료형 및 체크섬 (Phase 11).

원본: `Kernel/BusmasterDriverInterface/Include/LINDriverDefines.h`의
`STLIN_MSG`를 포팅. 체크섬·패리티는 LIN 2.x / ISO 17987 표준.

- 보호 ID (Protected ID): 6비트 프레임 ID + 2비트 패리티
    P0 = ID0^ID1^ID2^ID4, P1 = ~(ID1^ID3^ID4^ID5)
- 체크섬: 반전 8비트 합 (올림 포함)
    - 클래식: 데이터 바이트만 (진단 프레임 0x3C/0x3D는 항상 클래식)
    - 향상: 보호 ID + 데이터 바이트
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

DIAG_MASTER_REQ_ID = 0x3C
DIAG_SLAVE_RESP_ID = 0x3D


class ChecksumType(Enum):
    CLASSIC = "classic"
    ENHANCED = "enhanced"


def protected_id(frame_id: int) -> int:
    """6비트 프레임 ID → 보호 ID (패리티 비트 포함)."""
    fid = frame_id & 0x3F
    b = [(fid >> i) & 1 for i in range(6)]
    p0 = b[0] ^ b[1] ^ b[2] ^ b[4]
    p1 = 1 ^ (b[1] ^ b[3] ^ b[4] ^ b[5])
    return (p1 << 7) | (p0 << 6) | fid


def verify_parity(pid: int) -> bool:
    """보호 ID의 패리티가 올바른지."""
    return protected_id(pid & 0x3F) == (pid & 0xFF)


def calc_checksum(pid: int, data: bytes,
                  checksum_type: ChecksumType = ChecksumType.ENHANCED) -> int:
    """LIN 체크섬 계산."""
    total = 0
    if checksum_type == ChecksumType.ENHANCED:
        total += pid & 0xFF
    for byte in data:
        total += byte
        if total > 0xFF:
            total -= 0xFF  # 올림을 다시 더함
    if total > 0xFF:  # PID를 더한 뒤 한 번 더 넘을 수 있음
        total -= 0xFF
    return (~total) & 0xFF


def auto_checksum_type(frame_id: int) -> ChecksumType:
    """진단 ID(0x3C/0x3D)는 클래식, 나머지는 향상."""
    if frame_id in (DIAG_MASTER_REQ_ID, DIAG_SLAVE_RESP_ID):
        return ChecksumType.CLASSIC
    return ChecksumType.ENHANCED


@dataclass
class LinFrame:
    """LIN 프레임. 원본 `STLIN_MSG`에 대응."""

    frame_id: int = 0          # 6비트 프레임 ID
    data: bytes = b""          # 0..8 바이트
    channel: int = 1
    is_header: bool = False    # True면 헤더만 (응답 없음)
    checksum: int | None = None
    checksum_type: ChecksumType | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.frame_id <= 0x3F:
            raise ValueError(f"LIN frame ID 범위 초과: {self.frame_id:#x}")
        if len(self.data) > 8:
            raise ValueError("LIN 데이터는 최대 8바이트")
        if self.checksum_type is None:
            self.checksum_type = auto_checksum_type(self.frame_id)

    @property
    def pid(self) -> int:
        return protected_id(self.frame_id)

    def compute_checksum(self) -> int:
        return calc_checksum(self.pid, self.data, self.checksum_type)

    def verify(self) -> bool:
        """체크섬 검증. checksum이 없으면 계산값으로 간주해 True."""
        if self.checksum is None:
            return True
        return self.checksum == self.compute_checksum()
