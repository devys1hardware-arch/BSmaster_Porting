"""가상 노드 (Phase 8).

원본 BUSMASTER `NodeSimEx/`는 C 스크립트(`OnMessage_*`, `OnTimer_*` 핸들러)를
컴파일해 실행하는 방식이다. Python 포팅에서는 같은 개념을
Python 클래스로 재설계한다: 사용자는 `VirtualNode`를 상속받아
핸들러를 오버라이드한다.

- `on_start()` / `on_stop()`: 노드 시작/정지 시 호출
- `on_frame(frame)`: 버스 프레임 수신 시 호출
- `every(ms, callback)`: 주기 타이머 등록
- `send_can()` / `send_signals()`: 프레임 송신 (DBC 시그널 지원)
"""

from __future__ import annotations

from bsmaster.core.msgsignal import DbMessage, encode_signal, to_raw
from bsmaster.logconv.frames import LogFrame


class VirtualNode:
    """가상 노드 베이스 클래스. 상속받아 핸들러를 구현한다."""

    def __init__(self, name: str = "") -> None:
        self.name = name or self.__class__.__name__
        self._bus = None
        self._timers: list[list] = []  # [period_s, callback, next_fire]

    # -- 사용자 오버라이드 지점 --------------------------------------

    def on_start(self) -> None:
        """노드 시작 시 호출."""

    def on_stop(self) -> None:
        """노드 정지 시 호출."""

    def on_frame(self, frame: LogFrame) -> None:
        """버스 프레임 수신 시 호출."""

    # -- 노드 API ----------------------------------------------------

    def every(self, period_ms: float, callback) -> None:
        """주기 타이머 등록. callback은 인자 없이 호출된다."""
        period = period_ms / 1000.0
        self._timers.append([period, callback, period])

    def send(self, frame: LogFrame) -> None:
        """프레임을 버스에 송신."""
        if self._bus is None:
            raise RuntimeError("노드가 버스에 연결되지 않았습니다")
        self._bus._emit(self, frame)

    def send_can(self, msg_id: int, data: bytes, channel: int = 1,
                 extended: bool = False, direction: str = "Tx") -> LogFrame:
        """CAN 프레임 송신."""
        frame = LogFrame(channel=channel, msg_id=msg_id, extended=extended,
                         direction=direction, data=bytes(data))
        self.send(frame)
        return frame

    def send_signals(self, message: DbMessage, values: dict) -> LogFrame:
        """DBC 메시지 정의 + 물리값 dict로 프레임 조립 후 송신.

        예: node.send_signals(db.get_by_id(0x100), {"RPM": 3000.0})
        """
        data = bytearray(message.length)
        for sig in message.signals:
            if sig.name in values:
                encode_signal(sig, data, to_raw(sig, values[sig.name]))
        return self.send_can(message.code, bytes(data),
                             extended=message.extended)
