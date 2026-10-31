"""핵심 CAN 데이터 타입.

BUSMASTER 원본 `Sources/BUSMASTER/Include/Struct_CAN_.h` 의
`sTCAN_MSG` / `sCAN_ERR` 및 관련 enum을 Python으로 포팅한 것이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

#: CAN FD 최대 데이터 길이 (원본: `m_ucData[64]`)
MAX_CANFD_DATA_LEN = 64

#: 클래식 CAN 최대 데이터 길이
MAX_CAN_DATA_LEN = 8


class ControllerMode(IntEnum):
    """원본 `defMODE`."""

    ACTIVE = 1
    PASSIVE = 2
    SIMULATE = 3


class ControllerState(IntEnum):
    """원본 `defCONTROLLER`."""

    ACTIVE = 1
    PASSIVE = 2
    BUSOFF = 3


@dataclass
class CanFrame:
    """CAN(FD) 프레임. 원본 `STCAN_MSG` (`sTCAN_MSG`)에 대응한다.

    Attributes:
        msg_id: 11비트 또는 29비트 메시지 ID (원본 `m_unMsgID`).
        extended: True면 29비트 확장 프레임 (원본 `m_ucEXTENDED`).
        rtr: True면 Remote Transmission Request (원본 `m_ucRTR`).
        channel: 채널 번호 (원본 `m_ucChannel`).
        data: 데이터 바이트, 최대 64바이트 (원본 `m_ucData[64]`).
        is_canfd: True면 CAN FD 프레임 (원본 `m_bCANFD`).
    """

    msg_id: int = 0
    extended: bool = False
    rtr: bool = False
    channel: int = 0
    data: bytes = b""
    is_canfd: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.msg_id <= 0x1FFFFFFF:
            raise ValueError(f"msg_id out of range: {self.msg_id:#x}")
        if not self.extended and self.msg_id > 0x7FF:
            raise ValueError(f"11-bit ID out of range: {self.msg_id:#x}")
        if len(self.data) > MAX_CANFD_DATA_LEN:
            raise ValueError(f"data too long: {len(self.data)} bytes")
        if not self.is_canfd and len(self.data) > MAX_CAN_DATA_LEN:
            raise ValueError(f"classic CAN data too long: {len(self.data)} bytes")

    @property
    def dlc(self) -> int:
        """데이터 길이 코드. 원본 `m_ucDataLen`에 대응한다."""
        return len(self.data)


@dataclass
class CanError:
    """에러 카운터 + 채널. 원본 `SCAN_ERR` (`sCAN_ERR`)에 대응한다."""

    tx_error: int = 0
    rx_error: int = 0
    channel: int = 0
