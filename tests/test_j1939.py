"""J1939 테스트 (Phase 6)."""

from bsmaster.j1939 import (
    J1939Message,
    J1939MsgType,
    compose,
    decompose,
)


def test_decompose_pdu2_eec1():
    # EEC1 (PGN 61444 = 0xF004): 0x0CF00400
    jid = decompose(0x0CF00400)
    assert jid.priority == 3
    assert jid.data_page == 0
    assert jid.pdu_format == 0xF0
    assert jid.pdu_specific == 0x04
    assert jid.src_address == 0x00
    assert not jid.is_pdu1
    assert jid.dest_address is None
    assert jid.pgn == 61444


def test_decompose_pdu1_request():
    # Request (PGN 59904 = 0xEA00), 목적지 0xFF, 소스 0x00: 0x18EAFF00
    jid = decompose(0x18EAFF00)
    assert jid.priority == 6
    assert jid.is_pdu1
    assert jid.dest_address == 0xFF
    assert jid.src_address == 0x00
    # PDU1: PS가 PGN에서 제외됨 (unGetPGN 마스크)
    assert jid.pgn == 59904


def test_compose_roundtrip():
    ext = compose(3, 61444, src_address=0x00)
    assert ext == 0x0CF00400
    ext = compose(6, 59904, src_address=0x00, dest_address=0xFF)
    assert ext == 0x18EAFF00
    jid = decompose(ext)
    assert jid.ext_id == ext


def test_compose_pdu2_keeps_group_extension():
    # PDU2는 PGN의 PS(그룹 확장)를 그대로 사용
    ext = compose(3, 0xF004, src_address=0x01)
    assert decompose(ext).pdu_specific == 0x04


def test_j1939_message():
    msg = J1939Message.from_can(0x0CF00400, b"\x01\x02\x03",
                                msg_type=J1939MsgType.BROADCAST)
    assert msg.pgn == 61444
    assert msg.msg_id.src_address == 0x00
    assert msg.data == b"\x01\x02\x03"
