"""핵심 데이터 타입 테스트."""

import pytest

from bsmaster.core.datatypes import (
    MAX_CAN_DATA_LEN,
    MAX_CANFD_DATA_LEN,
    CanError,
    CanFrame,
    ControllerMode,
    ControllerState,
)


def test_canframe_defaults():
    frame = CanFrame()
    assert frame.msg_id == 0
    assert frame.dlc == 0
    assert not frame.extended


def test_canframe_classic_data():
    frame = CanFrame(msg_id=0x123, data=bytes([1, 2, 3, 4, 5, 6, 7, 8]))
    assert frame.dlc == 8


def test_canframe_rejects_too_long_classic():
    with pytest.raises(ValueError):
        CanFrame(msg_id=0x123, data=bytes(9))


def test_canframe_canfd_up_to_64():
    frame = CanFrame(msg_id=0x123, data=bytes(64), is_canfd=True)
    assert frame.dlc == MAX_CANFD_DATA_LEN


def test_canframe_rejects_over_64():
    with pytest.raises(ValueError):
        CanFrame(msg_id=0x123, data=bytes(65), is_canfd=True)


def test_canframe_rejects_bad_11bit_id():
    with pytest.raises(ValueError):
        CanFrame(msg_id=0x800)


def test_canframe_extended_29bit_id():
    frame = CanFrame(msg_id=0x1FFFFFFF, extended=True)
    assert frame.msg_id == 0x1FFFFFFF


def test_canerror_defaults():
    err = CanError()
    assert err.tx_error == 0 and err.rx_error == 0


def test_enums():
    assert ControllerMode.ACTIVE == 1
    assert ControllerState.BUSOFF == 3
