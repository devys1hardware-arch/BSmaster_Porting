"""UDS 테스트 (Phase 7)."""

import pytest

from bsmaster.uds import (
    FlowControl,
    NegativeResponseCode,
    ServiceId,
    build_request,
    decode,
    encode,
    frame_type,
    parse_response,
    positive_response_sid,
)


def test_service_ids():
    assert ServiceId.DIAGNOSTIC_SESSION_CONTROL.value == 0x10
    assert ServiceId.READ_DATA_BY_IDENTIFIER.value == 0x22
    assert ServiceId.TESTER_PRESENT.value == 0x3E


def test_positive_response_sid():
    assert positive_response_sid(0x22) == 0x62
    assert positive_response_sid(0x10) == 0x50


def test_parse_positive_response():
    # 0x22 0xF1 0x90 요청에 대한 긍정 응답: 0x62 0xF1 0x90 <data>
    r = parse_response(bytes([0x62, 0xF1, 0x90, 0x01, 0x02]))
    assert r.positive
    assert r.service_id == 0x22
    assert r.data == bytes([0xF1, 0x90, 0x01, 0x02])
    assert r.nrc is None


def test_parse_negative_response():
    r = parse_response(bytes([0x7F, 0x22, 0x31]))
    assert not r.positive
    assert r.service_id == 0x22
    assert r.nrc == NegativeResponseCode.REQUEST_OUT_OF_RANGE


def test_parse_bad_response():
    with pytest.raises(ValueError):
        parse_response(b"")
    with pytest.raises(ValueError):
        parse_response(bytes([0x7F, 0x22]))


def test_build_request():
    assert build_request(ServiceId.TESTER_PRESENT, b"\x00") == b"\x3E\x00"
    assert build_request(0x22, b"\xF1\x90") == b"\x22\xF1\x90"


def test_isotp_single_frame():
    payload = b"\x3E\x00"
    frames = encode(payload)
    assert len(frames) == 1
    assert frames[0][0] == 0x02  # SF, 길이 2
    assert decode(frames) == payload


def test_isotp_single_frame_max():
    payload = bytes(range(7))
    assert decode(encode(payload)) == payload


def test_isotp_multi_frame():
    payload = bytes(range(20))  # FF + CF 2개
    frames = encode(payload)
    assert len(frames) == 3
    assert frames[0][0] >> 4 == 0x1  # FF
    assert frames[0][0] & 0xF == 0x0 and frames[0][1] == 20
    assert frames[1][0] == 0x21 and frames[2][0] == 0x22  # CF 시퀀스
    assert decode(frames) == payload


def test_isotp_sequence_wrap():
    payload = bytes(6 + 7 * 16)  # 시퀀스가 0xF를 넘어 0으로 감김
    frames = encode(payload)
    assert decode(frames) == payload
    seqs = [f[0] & 0xF for f in frames[1:]]
    # 명시적 검증: 1..F, 0
    assert seqs == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 0]


def test_isotp_bad_sequence():
    frames = encode(bytes(20))
    bad = [frames[0], bytes([0x23]) + frames[1][1:], frames[2]]
    with pytest.raises(ValueError):
        decode(bad)


def test_flow_control():
    fc = FlowControl(fs=0, block_size=8, st_min=10)
    raw = fc.encode()
    assert raw[0] == 0x30
    back = FlowControl.decode(raw)
    assert (back.fs, back.block_size, back.st_min) == (0, 8, 10)


def test_frame_type():
    assert frame_type(0x02) == "SingleFrame"
    assert frame_type(0x10) == "FirstFrame"
    assert frame_type(0x21) == "ConsecutiveFrame"
    assert frame_type(0x30) == "FlowControl"


def test_uds_over_isotp_roundtrip():
    # UDS 요청 → ISO-TP 인코딩 → 디코딩 → 응답 파싱 전체 흐름
    req = build_request(ServiceId.READ_DATA_BY_IDENTIFIER, b"\xF1\x90")
    wire = encode(req)
    assert decode(wire) == req
    resp = parse_response(bytes([0x62, 0xF1, 0x90, 0x0A]))
    assert resp.positive and resp.service_id == 0x22
