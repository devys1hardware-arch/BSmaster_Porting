"""msgsignal 모듈 테스트.

인코딩 벡터는 원본 C++(`sSIGNALS::vSetSignalValue`,
`sSIGNALS::un64GetBitMask`)의 비트 배치 규칙과 동일함을 검증한다.
"""

import random

import pytest

from bsmaster.core.msgsignal import (
    DbMessage,
    DbSignal,
    Endianness,
    InterpretedSignal,
    MessageDatabase,
    SignalValueType,
    TimingType,
    WaveformType,
    decode_signal,
    encode_signal,
    interpret_signal,
    signal_bitmask,
    to_physical,
    to_raw,
)


def intel_sig(**kw):
    args = dict(name="sig", start_byte=1, start_bit=0, length=8,
                endianness=Endianness.INTEL)
    args.update(kw)
    return DbSignal(**args)


def motorola_sig(**kw):
    args = dict(name="sig", start_byte=2, start_bit=0, length=16,
                endianness=Endianness.MOTOROLA)
    args.update(kw)
    return DbSignal(**args)


# --- Intel 인코딩 ---

def test_intel_byte_aligned():
    sig = intel_sig(length=8)
    data = bytearray(8)
    encode_signal(sig, data, 0xAB)
    assert data[0] == 0xAB
    assert decode_signal(sig, bytes(data)) == 0xAB


def test_intel_unaligned():
    # start_bit=4, len=8 → 비트 4..11 → data = [0xD0, 0x0C, ...]
    sig = intel_sig(start_bit=4, length=8)
    data = bytearray(8)
    encode_signal(sig, data, 0xCD)
    assert data[0] == 0xD0
    assert data[1] == 0x0C
    assert decode_signal(sig, bytes(data)) == 0xCD


def test_intel_two_signals_no_clobber():
    sig_a = intel_sig(name="a", start_bit=0, length=4)
    sig_b = intel_sig(name="b", start_bit=4, length=4)
    data = bytearray(8)
    encode_signal(sig_a, data, 0xA)
    encode_signal(sig_b, data, 0xB)
    assert data[0] == 0xBA
    assert decode_signal(sig_a, bytes(data)) == 0xA
    assert decode_signal(sig_b, bytes(data)) == 0xB


def test_value_masked_to_length():
    sig = intel_sig(length=8)
    data = bytearray(8)
    encode_signal(sig, data, 0x1FF)  # 9비트 값을 8비트 시그널에
    assert data[0] == 0xFF


def test_bitmask_intel():
    assert signal_bitmask(intel_sig(length=8)) == 0xFF
    assert signal_bitmask(intel_sig(start_byte=2, start_bit=0, length=8)) == 0xFF00


# --- Motorola 인코딩 ---

def test_motorola_known_vector():
    # DBC "7|16@0+" → BUSMASTER 내부 표현 (start_byte=2, start_bit=0).
    # 값 0x1234 → data[0]=0x12, data[1]=0x34 (빅엔디안 배치)
    sig = motorola_sig()
    data = bytearray(8)
    encode_signal(sig, data, 0x1234)
    assert data[0] == 0x12
    assert data[1] == 0x34
    assert decode_signal(sig, bytes(data)) == 0x1234


def test_bitmask_motorola():
    assert signal_bitmask(motorola_sig()) == 0xFFFF


def _valid_combos():
    combos = []
    for sb in range(1, 9):
        for bit in range(8):
            for ln in (1, 4, 8, 12, 16):
                if (sb - 1) * 8 + bit + ln <= 64:
                    combos.append(("intel", sb, bit, ln))
                if ln <= sb * 8 - bit and sb * 8 - bit >= 1:
                    combos.append(("motorola", sb, bit, ln))
    return combos


def test_roundtrip_fuzz():
    rng = random.Random(42)
    for endian, sb, bit, ln in _valid_combos():
        sig = DbSignal(name="f", start_byte=sb, start_bit=bit, length=ln,
                       endianness=Endianness.INTEL if endian == "intel"
                       else Endianness.MOTOROLA)
        for _ in range(3):
            value = rng.randrange(1 << ln)
            data = bytearray(8)
            encode_signal(sig, data, value)
            assert decode_signal(sig, bytes(data)) == value, \
                f"{endian} sb={sb} bit={bit} len={ln} val={value:#x}"


# --- 물리값 변환 ---

def test_physical_conversion():
    sig = intel_sig(factor=0.1, offset=0.0, unit="km/h")
    assert to_physical(sig, 600) == pytest.approx(60.0)
    assert to_raw(sig, 60.0) == 600


def test_signed_interpretation():
    sig = intel_sig(length=8, signal_type=SignalValueType.INT)
    assert to_physical(sig, 0xFF) == pytest.approx(-1.0)
    sig_u = intel_sig(length=8, signal_type=SignalValueType.UINT)
    assert to_physical(sig_u, 0xFF) == pytest.approx(255.0)


def test_interpret_signal_with_desc():
    sig = intel_sig(length=8, unit="km/h",
                    desc_values=[("OFF", 0), ("ON", 1)])
    data = bytearray(8)
    encode_signal(sig, data, 1)
    info = interpret_signal(sig, bytes(data))
    assert isinstance(info, InterpretedSignal)
    assert info.signal_name == "sig"
    assert info.raw_value == 1
    assert info.desc_value == "ON"
    assert info.unit == "km/h"


# --- 데이터베이스 ---

def test_message_database():
    db = MessageDatabase()
    assert len(db) == 0
    msg = DbMessage(name="Engine", code=0x100,
                    signals=[intel_sig(name="rpm")])
    db.add_message(msg)
    assert len(db) == 1
    assert db.get_by_id(0x100) is msg
    assert db.get_by_name("Engine") is msg
    assert db.get_by_id(0x999) is None
    assert db.message_ids() == [0x100]
    assert msg.get_signal("rpm") is not None
    assert msg.get_signal("nope") is None
    assert db.remove_by_id(0x100) is True
    assert len(db) == 0
    assert db.remove_by_id(0x100) is False


# --- 유효성 검사 ---

def test_signal_validation():
    with pytest.raises(ValueError):
        DbSignal(start_byte=0)
    with pytest.raises(ValueError):
        DbSignal(start_bit=8)
    with pytest.raises(ValueError):
        DbSignal(length=65)
    with pytest.raises(ValueError):
        encode_signal(intel_sig(), bytearray(4), 1)


def test_enums():
    assert Endianness.MOTOROLA == 0
    assert Endianness.INTEL == 1
    assert WaveformType.SINE == 1
    assert TimingType.CYCLIC == 1
