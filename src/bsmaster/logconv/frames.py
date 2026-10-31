"""로그 프레임 공통 자료형.

ASC/BLF 리더·라이터가 공유하는 로그 한 줄(프레임) 표현.
원본 BUSMASTER는 `STCAN_MSG`에 타임스탬프·방향을 덧붙여 썼는데,
여기서는 로그 전용 `LogFrame`으로 분리한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bsmaster.core.datatypes import CanFrame


@dataclass
class LogFrame:
    """로그 파일의 CAN 프레임 한 건.

    Attributes:
        timestamp: 초 단위 타임스탬프.
        channel: 채널 번호 (1부터 시작, ASC/BLF 관례).
        msg_id: 11비트 또는 29비트 메시지 ID.
        extended: True면 29비트 확장 프레임.
        direction: "Rx" 또는 "Tx".
        data: 데이터 바이트.
        is_canfd: True면 CAN FD 프레임.
        flags: 원본 포맷의 플래그 바이트 (BLF raw flags 등).
    """

    timestamp: float = 0.0
    channel: int = 1
    msg_id: int = 0
    extended: bool = False
    direction: str = "Rx"
    data: bytes = b""
    is_canfd: bool = False
    flags: int = 0

    def to_can_frame(self) -> CanFrame:
        """`core.datatypes.CanFrame`으로 변환 (타임스탬프·방향 제외)."""
        return CanFrame(
            msg_id=self.msg_id,
            extended=self.extended,
            channel=self.channel,
            data=self.data,
            is_canfd=self.is_canfd,
        )

    @classmethod
    def from_can_frame(
        cls, frame: CanFrame, timestamp: float = 0.0, direction: str = "Rx"
    ) -> "LogFrame":
        return cls(
            timestamp=timestamp,
            channel=frame.channel,
            msg_id=frame.msg_id,
            extended=frame.extended,
            direction=direction,
            data=frame.data,
            is_canfd=frame.is_canfd,
        )
