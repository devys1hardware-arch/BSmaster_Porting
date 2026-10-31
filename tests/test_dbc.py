"""DBC 파서 테스트."""

import pytest

from bsmaster.core.msgsignal import (
    Endianness,
    SignalValueType,
    decode_signal,
    encode_signal,
    to_physical,
)
from bsmaster.dbc.parser import (
    DbcDatabase,
    _dbc_to_internal_start,
    parse_text,
)

SAMPLE_DBC = """VERSION "test dbc 1.0"

NS_ :
    NS_DESC_
    CM_
    BA_DEF_

BS_ :

BU_: Engine ABS

BO_ 256 EngineData: 8 Vector__XXX
 SG_ RPM : 0|16@1+ (0.125,0) [0|8000] "rpm" Vector__XXX
 SG_ Temp : 16|8@1- (1,-40) [-40|215] "degC" Vector__XXX
 SG_ WheelSpeed : 7|16@0+ (0.1,0) [0|6553.5] "km/h" ABS
 SG_ Voltage : 32|32@1+ (0.001,0) [0|50] "V" Vector__XXX

BO_ 2147483650 ExtMsg: 8 Vector__XXX
 SG_ Status : 0|8@1+ (1,0) [0|255] "" Vector__XXX

BO_ 512 MuxMsg: 8 Vector__XXX
 SG_ Mux m0 : 0|8@1+ (1,0) [0|255] "" Vector__XXX
 SG_ SigA m1 : 8|8@1+ (1,0) [0|255] "" Vector__XXX

VAL_ 256 Temp 0 "Cold" 1 "Hot" ;

SIG_VALTYPE_ 256 Voltage : 1;

CM_ BO_ 256 "Engine data message";
CM_ SG_ 256 RPM "Engine RPM signal";
"""


@pytest.fixture()
def db() -> DbcDatabase:
    return parse_text(SAMPLE_DBC)


def test_meta(db):
    assert db.version == "test dbc 1.0"
    assert db.nodes == ["Engine", "ABS"]
    assert len(db) == 3


def test_message_fields(db):
    msg = db.get_by_id(0x100)
    assert msg is not None
    assert msg.name == "EngineData"
    assert msg.length == 8
    assert msg.transmitter == "Vector__XXX"
    assert not msg.extended
    assert msg.comment == "Engine data message"
    assert len(msg.signals) == 4


def test_extended_id(db):
    msg = db.get_by_id(2)
    assert msg is not None
    assert msg.name == "ExtMsg"
    assert msg.extended


def test_intel_signal(db):
    sig = db.get_by_id(0x100).get_signal("RPM")
    assert sig.start_byte == 1 and sig.start_bit == 0
    assert sig.length == 16
    assert sig.endianness == Endianness.INTEL
    assert sig.factor == pytest.approx(0.125)
    assert sig.unit == "rpm"
    assert sig.comment == "Engine RPM signal"


def test_signed_signal(db):
    sig = db.get_by_id(0x100).get_signal("Temp")
    assert sig.signal_type == SignalValueType.INT
    assert sig.start_byte == 3 and sig.start_bit == 0
    assert sig.offset == pytest.approx(-40.0)
    assert sig.desc_values == [("Cold", 0), ("Hot", 1)]


def test_motorola_signal(db):
    # DBC "7|16@0+" → BUSMASTER 내부 표현 (2, 0)
    sig = db.get_by_id(0x100).get_signal("WheelSpeed")
    assert sig.endianness == Endianness.MOTOROLA
    assert (sig.start_byte, sig.start_bit) == (2, 0)


def test_float_sig_valtype(db):
    sig = db.get_by_id(0x100).get_signal("Voltage")
    assert sig.signal_type == SignalValueType.FLOAT


def test_multiplexer(db):
    msg = db.get_by_id(512)
    mux = msg.get_signal("Mux")
    siga = msg.get_signal("SigA")
    assert mux.multiplexor is True
    assert siga.multiplexor is False
    assert siga.multiplex_ids == [1]


def test_start_bit_conversion_vectors():
    # DBC 시작비트 → 내부 (start_byte, start_bit), DBFSignal.cpp 규칙
    assert _dbc_to_internal_start(0, 16, False, 8) == (1, 0)
    assert _dbc_to_internal_start(4, 12, False, 8) == (1, 4)
    assert _dbc_to_internal_start(7, 16, True, 8) == (2, 0)
    assert _dbc_to_internal_start(16, 8, False, 8) == (3, 0)


def test_parse_encode_integration(db):
    # 파싱한 시그널 정의로 Phase 1 인코딩이 그대로 동작
    msg = db.get_by_id(0x100)
    rpm = msg.get_signal("RPM")
    data = bytearray(8)
    encode_signal(rpm, data, 600)
    assert decode_signal(rpm, bytes(data)) == 600
    assert to_physical(rpm, 600) == pytest.approx(75.0)

    ws = msg.get_signal("WheelSpeed")
    data = bytearray(8)
    encode_signal(ws, data, 0x1234)
    assert data[0] == 0x12 and data[1] == 0x34
    assert decode_signal(ws, bytes(data)) == 0x1234


def test_ignores_unknown_sections():
    db = parse_text("BA_ \"Attr\" INT 0 100;\nEV_ SomeEvent : 1 [0|1] \"\" 0 1 0 Vector__XXX;\n")
    assert len(db) == 0
