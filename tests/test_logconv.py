"""로그 컨버터(ASC/BLF) 테스트."""

import pytest

from bsmaster.logconv.asc import parse_line, read_asc, write_asc
from bsmaster.logconv.blf import read_blf, write_blf
from bsmaster.logconv.frames import LogFrame

SAMPLE_ASC = """date Tue Oct 31 10:00:00 2026
base hex  timestamps absolute
internal events logged
// version 1.0
   0.000000 1  100             Rx   d 8 01 02 03 04 05 06 07 08
   0.001000 2  18DAF110        Tx   d 4 AA BB CC DD
   0.002000 1  200             Rx   d 0
"""


def test_parse_classic_line():
    f = parse_line("   0.000000 1  100             Rx   d 8 01 02 03 04 05 06 07 08")
    assert f is not None
    assert f.timestamp == pytest.approx(0.0)
    assert f.channel == 1
    assert f.msg_id == 0x100
    assert not f.extended
    assert f.direction == "Rx"
    assert f.data == bytes([1, 2, 3, 4, 5, 6, 7, 8])


def test_parse_extended_and_tx():
    f = parse_line("   0.001000 2  18DAF110        Tx   d 4 AA BB CC DD")
    assert f is not None
    assert f.extended
    assert f.msg_id == 0x18DAF110
    assert f.direction == "Tx"
    assert f.data == bytes([0xAA, 0xBB, 0xCC, 0xDD])


def test_parse_skips_non_frames():
    assert parse_line("date Tue Oct 31 10:00:00 2026") is None
    assert parse_line("base hex  timestamps absolute") is None
    assert parse_line("// comment") is None
    assert parse_line("") is None


def test_asc_roundtrip(tmp_path):
    p = tmp_path / "t.asc"
    p.write_text(SAMPLE_ASC, encoding="utf-8")
    frames = read_asc(str(p))
    assert len(frames) == 3
    assert frames[2].data == b""

    out = tmp_path / "o.asc"
    write_asc(str(out), frames)
    frames2 = read_asc(str(out))
    assert len(frames2) == 3
    for a, b in zip(frames, frames2):
        assert a.msg_id == b.msg_id
        assert a.data == b.data
        assert a.direction == b.direction
        assert a.timestamp == pytest.approx(b.timestamp)


def test_blf_roundtrip(tmp_path):
    frames = [
        LogFrame(timestamp=0.0, channel=1, msg_id=0x100,
                 direction="Rx", data=bytes([1, 2, 3, 4])),
        LogFrame(timestamp=1.5, channel=2, msg_id=0x18DAF110, extended=True,
                 direction="Tx", data=bytes(range(8))),
    ]
    p = tmp_path / "t.blf"
    write_blf(str(p), frames)
    back = read_blf(str(p))
    assert len(back) == 2
    assert back[0].msg_id == 0x100 and not back[0].extended
    assert back[0].data == bytes([1, 2, 3, 4])
    assert back[0].direction == "Rx"
    assert back[0].timestamp == pytest.approx(0.0)
    assert back[1].extended and back[1].msg_id == 0x18DAF110
    assert back[1].direction == "Tx"
    assert back[1].timestamp == pytest.approx(1.5)


def test_blf_bad_signature(tmp_path):
    p = tmp_path / "bad.blf"
    p.write_bytes(b"\x00" * 144)
    with pytest.raises(ValueError):
        read_blf(str(p))


def test_logframe_canframe_bridge():
    f = LogFrame(timestamp=2.0, channel=3, msg_id=0x200,
                 direction="Tx", data=b"\x01\x02")
    cf = f.to_can_frame()
    assert cf.msg_id == 0x200 and cf.channel == 3
    back = LogFrame.from_can_frame(cf, timestamp=2.0, direction="Tx")
    assert back.msg_id == 0x200 and back.direction == "Tx"
