"""메시지 필터 테스트 (Phase 5)."""

from bsmaster.core.datatypes import CanFrame
from bsmaster.core.filters import (
    CanFilter,
    Direction,
    FilterKind,
    FilterSet,
    IdType,
    MsgType,
)
from bsmaster.logconv.frames import LogFrame


def _frame(**kw):
    base = dict(timestamp=0.0, channel=1, msg_id=0x100, direction="Rx",
                data=b"\x01\x02")
    base.update(kw)
    return LogFrame(**base)


def test_single_id_match():
    f = CanFilter(kind=FilterKind.SINGLE_ID, id_from=0x100)
    assert f.matches(_frame())
    assert not f.matches(_frame(msg_id=0x200))


def test_id_range_match():
    f = CanFilter(kind=FilterKind.ID_RANGE, id_from=0x100, id_to=0x1FF)
    assert f.matches(_frame(msg_id=0x100))
    assert f.matches(_frame(msg_id=0x1FF))
    assert not f.matches(_frame(msg_id=0x200))
    assert not f.matches(_frame(msg_id=0xFF))


def test_direction_filter():
    f = CanFilter(kind=FilterKind.SINGLE_ID, id_from=0x100,
                  direction=Direction.TX)
    assert not f.matches(_frame(direction="Rx"))
    assert f.matches(_frame(direction="Tx"))


def test_channel_filter():
    f = CanFilter(kind=FilterKind.SINGLE_ID, id_from=0x100, channel=2)
    assert not f.matches(_frame(channel=1))
    assert f.matches(_frame(channel=2))


def test_id_type_filter():
    f = CanFilter(kind=FilterKind.ID_RANGE, id_from=0, id_to=0x1FFFFFFF,
                  id_type=IdType.EXTENDED)
    assert not f.matches(_frame(msg_id=0x100, extended=False))
    assert f.matches(_frame(msg_id=0x100, extended=True))


def test_rtr_filter():
    f = CanFilter(kind=FilterKind.SINGLE_ID, id_from=0x100,
                  msg_type=MsgType.RTR)
    assert not f.matches(CanFrame(msg_id=0x100, rtr=False))
    assert f.matches(CanFrame(msg_id=0x100, rtr=True))


def test_filterset_pass_mode():
    fs = FilterSet(mode="pass", filters=[
        CanFilter(kind=FilterKind.SINGLE_ID, id_from=0x100)])
    assert fs.passes(_frame(msg_id=0x100))
    assert not fs.passes(_frame(msg_id=0x200))


def test_filterset_stop_mode():
    fs = FilterSet(mode="stop", filters=[
        CanFilter(kind=FilterKind.SINGLE_ID, id_from=0x100)])
    assert not fs.passes(_frame(msg_id=0x100))
    assert fs.passes(_frame(msg_id=0x200))


def test_filterset_disabled_or_empty():
    fs = FilterSet(mode="pass", filters=[
        CanFilter(kind=FilterKind.SINGLE_ID, id_from=0x100)], enabled=False)
    assert fs.passes(_frame(msg_id=0x200))
    assert FilterSet().passes(_frame(msg_id=0x200))


def test_filter_frames():
    fs = FilterSet(mode="pass", filters=[
        CanFilter(kind=FilterKind.ID_RANGE, id_from=0x100, id_to=0x10F)])
    frames = [_frame(msg_id=0x100), _frame(msg_id=0x200), _frame(msg_id=0x105)]
    out = fs.filter_frames(frames)
    assert [f.msg_id for f in out] == [0x100, 0x105]
