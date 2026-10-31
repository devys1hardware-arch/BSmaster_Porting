"""LIN 테스트 (Phase 11)."""

import pytest

from bsmaster.lin import (
    ChecksumType,
    LinFrame,
    auto_checksum_type,
    calc_checksum,
    protected_id,
    verify_parity,
)


def test_protected_id_vectors():
    # 교과서 벡터
    assert protected_id(0x00) == 0x80
    assert protected_id(0x3C) == 0x3C  # 진단 마스터 요청
    assert protected_id(0x35) == 0xF5
    assert protected_id(0x3D) == 0x7D  # 진단 슬레이브 응답


def test_verify_parity():
    assert verify_parity(0xF5)
    assert verify_parity(0x3C)
    assert not verify_parity(0xF4)  # 패리티 깨짐


def test_checksum_classic():
    # 데이터 [0x01, 0x02]: 합 3 → 반전 0xFC
    assert calc_checksum(0x80, b"\x01\x02", ChecksumType.CLASSIC) == 0xFC


def test_checksum_enhanced():
    # PID 0x80 + [0x01, 0x02]: 합 0x83 → 반전 0x7C
    assert calc_checksum(0x80, b"\x01\x02", ChecksumType.ENHANCED) == 0x7C


def test_checksum_carry():
    # 올림 처리: 0xFF + 0x01 = 0x100 → 0x01 → 반전 0xFE
    assert calc_checksum(0x00, b"\xFF\x01", ChecksumType.CLASSIC) == 0xFE


def test_auto_checksum_type():
    assert auto_checksum_type(0x3C) == ChecksumType.CLASSIC
    assert auto_checksum_type(0x3D) == ChecksumType.CLASSIC
    assert auto_checksum_type(0x10) == ChecksumType.ENHANCED


def test_lin_frame():
    f = LinFrame(frame_id=0x35, data=b"\x01\x02\x03")
    assert f.pid == 0xF5
    assert f.checksum_type == ChecksumType.ENHANCED
    cs = f.compute_checksum()
    f2 = LinFrame(frame_id=0x35, data=b"\x01\x02\x03", checksum=cs)
    assert f2.verify()
    f3 = LinFrame(frame_id=0x35, data=b"\x01\x02\x03", checksum=cs ^ 0xFF)
    assert not f3.verify()


def test_lin_frame_validation():
    with pytest.raises(ValueError):
        LinFrame(frame_id=0x40)
    with pytest.raises(ValueError):
        LinFrame(frame_id=0x01, data=b"\x00" * 9)
