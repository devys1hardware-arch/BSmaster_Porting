"""BLF(Vector Binary Logging Format) 리더/라이터 (Phase 3).

원본: `Format Converter/BlfLibrary` (`BlfFormat.h`, `BlfLibrary.cpp`).
구조체 레이아웃·오브젝트 크기 규칙·zlib 압축 컨테이너 처리를 그대로 따른다.

지원: 파일 헤더, LOG_CONTAINER(타입 10, zlib 압축),
CAN_MESSAGE(타입 1). 모르는 오브젝트 타입은 건너뛴다
(원본도 "info" 수준으로 스킵한다).

참고:
- `m_ObjectSize`는 16바이트 기본 헤더를 포함한 크기다.
- 오브젝트는 4바이트 경계에 패딩된다.
- 타임스탬프는 TIME_ONE_NANS 기준 나노초 → 초로 변환한다.
- CAN_MESSAGE의 flags 바이트(방향·RTR)는 원본이 raw로 전달하므로,
  여기서는 관례상 bit0을 Tx 표시로 해석한다.
"""

from __future__ import annotations

import struct
import zlib

from bsmaster.logconv.frames import LogFrame

_SIG_FILE = 0x47474F4C  # "LOGG"
_SIG_OBJ = 0x4A424F4C  # "LOBJ"

_TYPE_CAN_MESSAGE = 1
_TYPE_LOG_CONTAINER = 10

_FLAG_TIME_ONE_NANS = 1

_FILE_HEADER_FMT = "<II8BQQII16s16s72s"
_FILE_HEADER_SIZE = struct.calcsize(_FILE_HEADER_FMT)  # 144

_OBJ_BASE_FMT = "<IHHII"
_OBJ_BASE_SIZE = struct.calcsize(_OBJ_BASE_FMT)  # 16

_OBJ_HEADER_FMT = "<IHH"  # flags, notUsed, version
_OBJ_HEADER_REST = struct.calcsize(_OBJ_HEADER_FMT)  # 8
_OBJ_FULL_HEADER_SIZE = _OBJ_BASE_SIZE + _OBJ_HEADER_REST + 8  # 32 (타임스탬프 Q 포함)

_CAN_MSG_BODY_FMT = "<HBBI8s"
_CAN_MSG_BODY_SIZE = struct.calcsize(_CAN_MSG_BODY_FMT)  # 16
_CAN_MSG_OBJ_SIZE = _OBJ_FULL_HEADER_SIZE + _CAN_MSG_BODY_SIZE  # 48

_CONTAINER_REST_SIZE = 16  # flags(I) + notUsed(H) + version(H) + sizeUncompressed(Q)
_CONTAINER_HEADER_SIZE = _OBJ_BASE_SIZE + _CONTAINER_REST_SIZE  # 32


def _pad4(size: int) -> int:
    return (size + 3) & ~3


def _iter_objects(buf: bytes):
    """버퍼에서 (타입, 페이로드) 오브젝트를 순서대로 뽑는다.

    페이로드 = 기본 헤더(16B) 이후의 바이트 (패딩 제외).
    """
    pos = 0
    total = len(buf)
    while pos + _OBJ_BASE_SIZE <= total:
        sig, _hsize, _hver, obj_size, obj_type = struct.unpack_from(
            _OBJ_BASE_FMT, buf, pos)
        if sig != _SIG_OBJ or obj_size < _OBJ_BASE_SIZE:
            break
        payload_end = pos + obj_size
        payload = buf[pos + _OBJ_BASE_SIZE:payload_end]
        yield obj_type, payload
        pos += _pad4(obj_size)


def _decode_can_message(payload: bytes) -> LogFrame | None:
    # payload = 풀 헤더 나머지(16B) + 바디(16B)
    if len(payload) < (_OBJ_FULL_HEADER_SIZE - _OBJ_BASE_SIZE) + _CAN_MSG_BODY_SIZE:
        return None
    flags, _not_used, _version = struct.unpack_from(
        _OBJ_HEADER_FMT, payload, 0)
    (timestamp_ns,) = struct.unpack_from("<Q", payload, _OBJ_HEADER_REST)
    body_off = _OBJ_FULL_HEADER_SIZE - _OBJ_BASE_SIZE
    channel, msg_flags, dlc, raw_id, data = struct.unpack_from(
        _CAN_MSG_BODY_FMT, payload, body_off)
    extended = bool(raw_id & 0x80000000)
    return LogFrame(
        timestamp=timestamp_ns / 1e9,
        channel=channel,
        msg_id=raw_id & 0x1FFFFFFF,
        extended=extended,
        direction="Tx" if msg_flags & 0x01 else "Rx",
        data=data[:dlc],
        flags=msg_flags,
    )


def read_blf(path: str) -> list[LogFrame]:
    """BLF 파일을 읽어 `LogFrame` 리스트 반환."""
    with open(path, "rb") as f:
        buf = f.read()
    if len(buf) < _FILE_HEADER_SIZE:
        raise ValueError("BLF 파일이 너무 짧습니다")
    (sig,) = struct.unpack_from("<I", buf, 0)
    if sig != _SIG_FILE:
        raise ValueError("BLF 시그니처('LOGG')가 아닙니다")

    frames: list[LogFrame] = []
    uncompressed = bytearray()

    def handle(obj_type: int, payload: bytes, out: list[LogFrame]) -> None:
        if obj_type == _TYPE_CAN_MESSAGE:
            frame = _decode_can_message(payload)
            if frame is not None:
                out.append(frame)
        # 다른 타입은 스킵 (원본과 동일)

    for obj_type, payload in _iter_objects(buf[_FILE_HEADER_SIZE:]):
        if obj_type == _TYPE_LOG_CONTAINER:
            if len(payload) < _CONTAINER_REST_SIZE:
                continue
            (_cflags, _n, _v, size_uncompressed) = struct.unpack_from(
                "<IHHQ", payload, 0)
            comp_size = len(payload) - _CONTAINER_REST_SIZE
            # objectSize 기준이 정확하면 남는 패딩은 제외
            comp = payload[_CONTAINER_REST_SIZE:]
            try:
                uncompressed += zlib.decompress(comp)
            except zlib.error:
                continue
        else:
            handle(obj_type, payload, frames)

    for obj_type, payload in _iter_objects(bytes(uncompressed)):
        handle(obj_type, payload, frames)

    return frames


def _encode_can_message(frame: LogFrame) -> bytes:
    timestamp_ns = int(frame.timestamp * 1e9)
    flags = 0x01 if frame.direction == "Tx" else 0x00
    data = frame.data[:8].ljust(8, b"\x00")
    raw_id = frame.msg_id | (0x80000000 if frame.extended else 0)
    header = struct.pack(
        _OBJ_BASE_FMT, _SIG_OBJ, _OBJ_FULL_HEADER_SIZE, 1,
        _CAN_MSG_OBJ_SIZE, _TYPE_CAN_MESSAGE)
    header += struct.pack(_OBJ_HEADER_FMT, 0, 0, 1)
    header += struct.pack("<Q", timestamp_ns)
    body = struct.pack(
        _CAN_MSG_BODY_FMT, frame.channel, flags, len(frame.data),
        raw_id, data)
    return header + body  # 48바이트 (4바이트 정렬됨)


def write_blf(path: str, frames: list[LogFrame]) -> None:
    """`LogFrame` 리스트를 BLF 파일로 저장 (zlib 압축 컨테이너 사용)."""
    plain = b"".join(_encode_can_message(f) for f in frames)
    comp = zlib.compress(plain)
    obj_size = _CONTAINER_HEADER_SIZE + len(comp)
    container = struct.pack(
        _OBJ_BASE_FMT, _SIG_OBJ, _CONTAINER_HEADER_SIZE, 1,
        obj_size, _TYPE_LOG_CONTAINER)
    container += struct.pack("<IHHQ", _FLAG_TIME_ONE_NANS, 0, 0, len(plain))
    container += comp
    container += b"\x00" * (_pad4(obj_size) - obj_size)

    file_size = _FILE_HEADER_SIZE + len(container)
    header = struct.pack(
        _FILE_HEADER_FMT,
        _SIG_FILE, _FILE_HEADER_SIZE,
        0, 0, 0, 0, 2, 8, 1, 0,   # 앱/BL API 버전 (관례값)
        file_size, file_size,      # fileSize, uncompressed
        len(frames), 0,            # 오브젝트 수
        b"\x00" * 16, b"\x00" * 16,
        b"\x00" * 72,
    )
    with open(path, "wb") as f:
        f.write(header)
        f.write(container)
