"""하드웨어 어댑터 테스트 (Phase 12).

실제 하드웨어 없이 변환 로직과 에러 처리만 검증한다.
"""

import pytest

from bsmaster.hw import (
    HardwareBus,
    can_message_to_logframe,
    logframe_to_can_message,
)
from bsmaster.logconv.frames import LogFrame

can = pytest.importorskip("can")


def test_logframe_to_can_message():
    f = LogFrame(timestamp=1.5, channel=2, msg_id=0x100,
                 direction="Tx", data=b"\x01\x02\x03")
    m = logframe_to_can_message(f)
    assert m.arbitration_id == 0x100
    assert not m.is_extended_id
    assert bytes(m.data) == b"\x01\x02\x03"
    assert not m.is_fd


def test_logframe_fd_extended():
    f = LogFrame(msg_id=0x18DAF110, extended=True, is_canfd=True,
                 data=bytes(range(16)))
    m = logframe_to_can_message(f)
    assert m.is_extended_id and m.is_fd
    assert len(m.data) == 16


def test_can_message_to_logframe_roundtrip():
    f = LogFrame(timestamp=2.0, channel=1, msg_id=0x200,
                 direction="Tx", data=b"\xAA\xBB")
    back = can_message_to_logframe(logframe_to_can_message(f))
    assert back.msg_id == 0x200
    assert back.data == b"\xAA\xBB"
    assert back.direction == "Rx"  # 수신 변환은 Rx
    assert back.timestamp == pytest.approx(2.0)


def test_open_invalid_interface_raises_helpful_error():
    with pytest.raises(RuntimeError, match="CAN 하드웨어 열기 실패"):
        HardwareBus(interface="no_such_interface_xyz", channel=0)
