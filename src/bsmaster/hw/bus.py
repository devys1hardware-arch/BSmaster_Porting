"""하드웨어 CAN 어댑터 (Phase 12).

`python-can` 기반. BUSMASTER 원본의 벤더 드라이버 DLL
(`CAN_Vector_XL`, `CAN_PEAK_USB` 등)은 클로즈드 바이너리라
이식할 수 없으므로, 표준 `python-can` 인터페이스로 대체한다.

지원 하드웨어 (Leo 사용 기준):
- Vector VN1630 — `vector` 인터페이스 (Vector XL Driver 필요, Windows)
- PEAK-System USB CAN FD — `pcan` 인터페이스 (PCAN-Basic API 필요)
- Kvaser — 나중에 추가 예정

`LogFrame` 단위 API라 `VirtualBus`와 같은 방식으로 쓴다:

    bus = HardwareBus.vector_vn1630(bitrate=500000)
    bus.send(LogFrame(msg_id=0x100, data=b"\\x01\\x02"))
    frame = bus.recv(timeout=1.0)
"""

from __future__ import annotations

from typing import Iterator

try:
    import can

    _CAN_AVAILABLE = True
except ImportError:  # pragma: no cover
    can = None  # type: ignore
    _CAN_AVAILABLE = False

from bsmaster.logconv.frames import LogFrame


def _require_can() -> None:
    if not _CAN_AVAILABLE:
        raise RuntimeError(
            "python-can이 설치되지 않았습니다: pip install python-can")


def logframe_to_can_message(frame: LogFrame):
    """`LogFrame` → `can.Message`."""
    _require_can()
    return can.Message(
        timestamp=frame.timestamp,
        arbitration_id=frame.msg_id,
        is_extended_id=frame.extended,
        channel=frame.channel,
        data=frame.data,
        is_fd=frame.is_canfd,
    )


def can_message_to_logframe(msg, direction: str = "Rx") -> LogFrame:
    """`can.Message` → `LogFrame` (수신은 Rx)."""
    return LogFrame(
        timestamp=msg.timestamp or 0.0,
        channel=msg.channel if isinstance(msg.channel, int) else 1,
        msg_id=msg.arbitration_id,
        extended=msg.is_extended_id,
        direction=direction,
        data=bytes(msg.data),
        is_canfd=msg.is_fd,
    )


class HardwareBus:
    """실제 CAN 하드웨어 버스 (`LogFrame` 단위 송수신)."""

    def __init__(self, *, interface: str, channel,
                 bitrate: int = 500000, fd: bool = False,
                 data_bitrate: int = 2000000, **kwargs) -> None:
        _require_can()
        params = dict(interface=interface, channel=channel,
                      bitrate=bitrate, **kwargs)
        if fd:
            params["fd"] = True
            params["data_bitrate"] = data_bitrate
        try:
            self._bus = can.Bus(**params)
        except Exception as e:
            raise RuntimeError(
                f"CAN 하드웨어 열기 실패 ({interface}/{channel}): {e}. "
                f"벤더 드라이버(XL Driver/PCAN-Basic)가 설치됐는지 확인하세요."
            ) from e
        self.interface = interface
        self.channel = channel

    @classmethod
    def vector_vn1630(cls, app_channel: int = 0, bitrate: int = 500000,
                      fd: bool = False, data_bitrate: int = 2000000,
                      **kwargs) -> "HardwareBus":
        """Vector VN1630 열기. app_channel은 XL Driver의 앱 채널 번호."""
        return cls(interface="vector", channel=app_channel, bitrate=bitrate,
                   fd=fd, data_bitrate=data_bitrate, **kwargs)

    @classmethod
    def peak_usb_fd(cls, channel: str = "PCAN_USBBUS1",
                    bitrate: int = 500000, data_bitrate: int = 2000000,
                    **kwargs) -> "HardwareBus":
        """PEAK-System USB CAN FD 열기. channel 예: "PCAN_USBBUS1"."""
        return cls(interface="pcan", channel=channel, bitrate=bitrate,
                   fd=True, data_bitrate=data_bitrate, **kwargs)

    def send(self, frame: LogFrame) -> None:
        self._bus.send(logframe_to_can_message(frame))

    def recv(self, timeout: float = 0.1) -> LogFrame | None:
        msg = self._bus.recv(timeout)
        return can_message_to_logframe(msg) if msg is not None else None

    def iter_frames(self, timeout: float = 0.1) -> Iterator[LogFrame]:
        """수신 제너레이터. 타임아웃돼도 계속 대기한다."""
        while True:
            frame = self.recv(timeout)
            if frame is not None:
                yield frame

    def shutdown(self) -> None:
        self._bus.shutdown()

    def __enter__(self) -> "HardwareBus":
        return self

    def __exit__(self, *exc) -> None:
        self.shutdown()
