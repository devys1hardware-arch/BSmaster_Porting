"""CAN 메시지 필터 (Phase 5).

원본: `DataTypes/Filter_Datatypes.h`의 `SFILTER`/`SFILTER_CAN`
(매칭 로직 `bDoesFrameOccur`)와 `Filter/` 모듈의 Pass/Stop 개념을 포팅.

- `CanFilter.matches()`: 원본 `bDoesFrameOccur`에 대응.
  단일 ID 또는 ID 범위 + 채널 + 방향 + ID 타입 + RTR 여부를 검사한다.
- `FilterSet`: 필터 모음. `mode="pass"`면 매칭되는 프레임만 통과
  (화이트리스트), `mode="stop"`이면 매칭되는 프레임을 차단(블랙리스트).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FilterKind(Enum):
    SINGLE_ID = 0  # defFILTER_TYPE_SINGLE_ID
    ID_RANGE = 1  # defFILTER_TYPE_ID_RANGE


class Direction(Enum):
    RX = "Rx"  # defSTR_MSG_DIR_RX
    TX = "Tx"  # defSTR_MSG_DIR_TX
    ALL = "All"  # defFILTER_IGNORE_DIRECTION


class IdType(Enum):
    STANDARD = "Std"  # defSTR_MSG_ID_TYPE_STD
    EXTENDED = "Ext"  # defSTR_MSG_ID_TYPE_EXTD
    ALL = "All"  # defFILTER_IGNORE_ID_TYPE


class MsgType(Enum):
    RTR = "RTR"  # defSTR_MSG_TYPE_RTR
    NON_RTR = "NonRTR"  # defSTR_MSG_TYPE_NON_RTR
    ALL = "All"  # defFILTER_IGNORE_MSG_TYPE


@dataclass
class CanFilter:
    """개별 필터. 원본 `SFILTER_CAN`에 대응."""

    name: str = ""
    kind: FilterKind = FilterKind.SINGLE_ID
    id_from: int = 0  # m_dwMsgIDFrom (단일 ID 모드에서는 비교 ID)
    id_to: int = 0  # m_dwMsgIDTo (범위 모드에서만 사용)
    direction: Direction = Direction.ALL  # m_eDrctn
    id_type: IdType = IdType.ALL  # m_byIDType
    msg_type: MsgType = MsgType.ALL  # m_byMsgType
    channel: int = 0  # m_eChannel, 0 = 전체 채널 (CAN_CHANNEL_ALL)

    def matches(self, frame) -> bool:
        """프레임이 이 필터에 걸리는지. `frame`은 CanFrame 또는 LogFrame."""
        msg_id = frame.msg_id
        if self.kind == FilterKind.SINGLE_ID:
            if msg_id != self.id_from:
                return False
        elif not self.id_from <= msg_id <= self.id_to:
            return False

        if self.channel != 0 and frame.channel != self.channel:
            return False

        if self.direction != Direction.ALL:
            want = "Rx" if self.direction == Direction.RX else "Tx"
            if getattr(frame, "direction", "Rx") != want:
                return False

        if self.id_type != IdType.ALL:
            want_ext = self.id_type == IdType.EXTENDED
            if frame.extended != want_ext:
                return False

        if self.msg_type != MsgType.ALL:
            want_rtr = self.msg_type == MsgType.RTR
            if getattr(frame, "rtr", False) != want_rtr:
                return False

        return True


@dataclass
class FilterSet:
    """필터 모음 + Pass/Stop 동작. 원본 `SFILTERAPPLIED_CAN` 개념에 대응."""

    name: str = ""
    mode: str = "pass"  # "pass" (화이트리스트) | "stop" (블랙리스트)
    filters: list[CanFilter] = field(default_factory=list)
    enabled: bool = True

    def passes(self, frame) -> bool:
        """프레임을 표시/처리해도 되는지."""
        if not self.enabled or not self.filters:
            return True
        matched = any(f.matches(frame) for f in self.filters)
        return matched if self.mode == "pass" else not matched

    def filter_frames(self, frames: list) -> list:
        """리스트에서 통과하는 프레임만 골라낸다."""
        return [f for f in frames if self.passes(f)]
