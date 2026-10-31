"""하드웨어 CAN 어댑터 (Phase 12).

벤더 드라이버 DLL 대신 `python-can` 사용.
- Vector VN1630, PEAK-System USB CAN FD 지원 (Kvaser는 추후)
"""

from bsmaster.hw.bus import (
    HardwareBus,
    can_message_to_logframe,
    logframe_to_can_message,
)

__all__ = [
    "HardwareBus",
    "can_message_to_logframe",
    "logframe_to_can_message",
]
