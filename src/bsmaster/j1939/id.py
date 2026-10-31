"""J1939 29비트 ID 분해/조립 (Phase 6).

원본: `Kernel/BusmasterDriverInterface/Include/J1939DriverDefines.h`의
`STRUCT_29_BIT_ID`/`UNION_PGN`/`unGetPGN`/`vSetPGN`을 포팅.

29비트 ID 비트 배치 (LSB부터):
    bit 0-7   : 소스 주소 (SA)
    bit 8-15  : PDU Specific (PS) — PF<240이면 목적지 주소, 아니면 그룹 확장
    bit 16-23 : PDU Format (PF)
    bit 24    : 데이터 페이지 (DP)
    bit 25    : 예약 (R)
    bit 26-28 : 우선순위

PGN = DP(1) | PF(8) | PS(8) 18비트.
단 PDU1(PF < 240)에서는 PS가 목적지 주소이므로 PGN에서 제외
(`unGetPGN`의 마스크 규칙 그대로).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class J1939MsgType(Enum):
    """원본 `EJ1939_MSG_TYPE`에 대응."""

    NONE = 0x0
    COMMAND = 0x1
    REQUEST = 0x2
    DATA = 0x3
    BROADCAST = 0x4
    ACKNOWLEDGEMENT = 0x5
    GROUP_FUNCTIONS = 0x6
    NM_ACL = 0x7
    NM_RQST_ACL = 0x8
    NM_CMD_ADDRESS = 0x9
    NM_TPCM_BAM = 0xA
    NM_TPCM_RTS = 0xB
    NM_TPCM_CTS = 0xC
    NM_TPCM_EOM_ACK = 0xD
    NM_TPCM_CON_ABORT = 0xE
    NM_TPDT = 0xF


PDU1_MAX_PF = 240  # PF < 240 이면 PDU1 (목적지 지정)
ADDRESS_ALL = 255
ADDRESS_NULL = 254
DEFAULT_PRIORITY = 0x7


@dataclass(frozen=True)
class J1939Id:
    """분해된 J1939 29비트 ID. 원본 `STRUCT_29_BIT_ID`에 대응."""

    priority: int       # bit 26-28
    data_page: int      # bit 24
    pdu_format: int     # bit 16-23 (PF)
    pdu_specific: int   # bit 8-15 (PS)
    src_address: int    # bit 0-7 (SA)

    @property
    def pgn(self) -> int:
        """`unGetPGN()`에 대응. PDU1이면 PS를 제외한다."""
        pgn = (self.data_page << 16) | (self.pdu_format << 8) | self.pdu_specific
        if self.pdu_format < PDU1_MAX_PF:
            pgn &= 0x3FF00
        return pgn

    @property
    def is_pdu1(self) -> bool:
        return self.pdu_format < PDU1_MAX_PF

    @property
    def dest_address(self) -> int | None:
        """PDU1일 때 목적지 주소, PDU2(브로드캐스트)면 None."""
        return self.pdu_specific if self.is_pdu1 else None

    @property
    def ext_id(self) -> int:
        """29비트 ID로 재조립."""
        return (
            ((self.priority & 0x7) << 26)
            | ((self.data_page & 0x1) << 24)
            | ((self.pdu_format & 0xFF) << 16)
            | ((self.pdu_specific & 0xFF) << 8)
            | (self.src_address & 0xFF)
        )


def decompose(ext_id: int) -> J1939Id:
    """29비트 ID를 분해한다."""
    return J1939Id(
        priority=(ext_id >> 26) & 0x7,
        data_page=(ext_id >> 24) & 0x1,
        pdu_format=(ext_id >> 16) & 0xFF,
        pdu_specific=(ext_id >> 8) & 0xFF,
        src_address=ext_id & 0xFF,
    )


def compose(priority: int, pgn: int, src_address: int,
            dest_address: int = ADDRESS_ALL) -> int:
    """`vSetPGN` + `Prepare_P2P_Id`에 대응. 필드들로 29비트 ID를 만든다.

    PDU1(PF < 240)이면 PS 자리에 목적지 주소를 넣고,
    PDU2면 PGN의 PS(그룹 확장)를 그대로 쓴다.
    """
    pgn &= 0x3FFFF
    pdu_format = (pgn >> 8) & 0xFF
    if pdu_format < PDU1_MAX_PF:
        pdu_specific = dest_address & 0xFF
    else:
        pdu_specific = pgn & 0xFF
    return J1939Id(
        priority=priority,
        data_page=(pgn >> 16) & 0x1,
        pdu_format=pdu_format,
        pdu_specific=pdu_specific,
        src_address=src_address,
    ).ext_id


@dataclass
class J1939Message:
    """J1939 메시지. 원본 `STJ1939_MSG`의 핵심 필드에 대응."""

    msg_id: J1939Id
    data: bytes = b""
    channel: int = 1
    direction: str = "Rx"
    msg_type: J1939MsgType = J1939MsgType.DATA
    timestamp: float = 0.0

    @property
    def pgn(self) -> int:
        return self.msg_id.pgn

    @classmethod
    def from_can(cls, ext_id: int, data: bytes, **kw) -> "J1939Message":
        return cls(msg_id=decompose(ext_id), data=data, **kw)
