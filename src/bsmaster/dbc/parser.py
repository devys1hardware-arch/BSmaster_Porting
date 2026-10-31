"""DBC 파일 파서 (Phase 2).

BUSMASTER 원본 `Format Converter/DBC2DBFConverterLibrary/` (특히
`DBFSignal.cpp`의 Motorola 시작 비트 변환 로직)를 Python으로 포팅.

지원 구문: VERSION, NS_, BS_, BU_, BO_, SG_ (멀티플렉서 포함),
VAL_, SIG_VALTYPE_, CM_ (메시지/시그널 코멘트).
BA_/EV_ 등 속성은 무시한다 (파싱 에러 없이 건너뜀).

사용법:
    from bsmaster.dbc.parser import parse_file
    db = parse_file("example.dbc")
    msg = db.get_by_id(0x100)
"""

from __future__ import annotations

import re

from bsmaster.core.msgsignal import (
    DbMessage,
    DbSignal,
    Endianness,
    MessageDatabase,
    SignalValueType,
)

#: DBC 확장 ID 플래그 (29비트). ID의 최상위 비트가 서 있으면 확장 프레임.
_EXTENDED_ID_FLAG = 0x80000000
_EXTENDED_ID_MASK = 0x1FFFFFFF

_BO_RE = re.compile(r"^BO_\s+(\d+)\s+(\w+)\s*:\s*(\d+)\s+(\S+)")
_SG_RE = re.compile(
    r"^\s*SG_\s+(\w+)"          # 시그널 이름
    r"(?:\s+m(\d+)([mM]?))?"    # 멀티플렉서 표기 (m<M>[m|M])
    r"\s*:\s*(\d+)\|(\d+)"      # 시작비트|길이
    r"@([01])([+-])"            # 바이트순서(0=Motorola) + 부호
    r"\s*\(\s*([^,]+?)\s*,\s*([^\)]+?)\s*\)"   # (factor, offset)
    r"\s*\[\s*([^|]+?)\s*\|\s*([^\]]+?)\s*\]"  # [min|max]
    r"\s*\"([^\"]*)\""          # "unit"
    r"\s*(.*)$"                 # 수신 노드들
)
_VAL_RE = re.compile(r"^VAL_\s+(\d+)\s+(\w+)\s+(.*?);")
_VAL_PAIR_RE = re.compile(r"(\d+)\s+\"([^\"]*)\"")
_SIG_VALTYPE_RE = re.compile(r"^SIG_VALTYPE_\s+(\d+)\s+(\w+)\s*:\s*([012])\s*;")
_BU_RE = re.compile(r"^BU_\s*:(.*)$")
_VERSION_RE = re.compile(r"^VERSION\s+\"(.*)\"\s*$")
_CM_SG_RE = re.compile(r"^CM_\s+SG_\s+(\d+)\s+(\w+)\s+\"(.*)\"\s*;\s*$")
_CM_BO_RE = re.compile(r"^CM_\s+BO_\s+(\d+)\s+\"(.*)\"\s*;\s*$")


class DbcDatabase(MessageDatabase):
    """DBC 파싱 결과. `MessageDatabase`에 DBC 메타정보를 덧붙인다."""

    def __init__(self) -> None:
        super().__init__()
        self.version: str = ""
        self.nodes: list[str] = []


def _dbc_to_internal_start(
    start_bit: int, length: int, motorola: bool, dlc: int
) -> tuple[int, int]:
    """DBC 시작 비트 → BUSMASTER 내부 (start_byte, start_bit).

    `DBFSignal.cpp`의 변환 로직을 그대로 옮김. Intel은 LSB 위치를
    그대로 쓰고, Motorola는 MSB→LSB 변환 후 리틀엔디안 번호로 뒤집는다.
    start_byte는 1부터 시작.
    """
    if not motorola:
        return start_bit // 8 + 1, start_bit % 8
    ui = start_bit
    ntemp = 0 if ui == 0 else ui % 4
    if ui % 8 <= 3:
        ui = ui + 7 - ntemp * 2
    else:
        ui = ui - 1 - ntemp * 2
    ui = ui + length - 1
    ui_x = dlc * 8 - 1 - ui
    return ui // 8 + 1, ui_x % 8


def _parse_signal(line: str, dlc: int) -> DbSignal | None:
    m = _SG_RE.match(line)
    if not m:
        return None
    (name, mux_val, mux_sfx, start_s, len_s, order_s, sign_s,
     factor_s, offset_s, min_s, max_s, unit, _receivers) = m.groups()

    start_bit = int(start_s)
    length = int(len_s)
    motorola = order_s == "0"
    signed = sign_s == "-"

    if length > 32:
        sig_type = SignalValueType.INT64 if signed else SignalValueType.UINT64
    else:
        sig_type = SignalValueType.INT if signed else SignalValueType.UINT

    start_byte, start_bit_int = _dbc_to_internal_start(
        start_bit, length, motorola, dlc)

    multiplexor = False
    multiplex_ids: list[int] = []
    if mux_val is not None:
        if mux_sfx == "M":
            multiplexor = True  # 확장 멀티플렉싱의 스위치
        elif mux_sfx == "m":
            multiplex_ids = [int(mux_val)]  # 확장 멀티플렉싱의 소속 값
        elif int(mux_val) == 0:
            multiplexor = True  # 표준 멀티플렉싱의 스위치 (m0)
        else:
            multiplex_ids = [int(mux_val)]

    try:
        min_value = int(float(min_s))
    except ValueError:
        min_value = 0
    try:
        max_value = int(float(max_s))
    except ValueError:
        max_value = 0

    return DbSignal(
        name=name,
        start_byte=start_byte,
        start_bit=start_bit_int,
        length=length,
        signal_type=sig_type,
        min_value=min_value,
        max_value=max_value,
        factor=float(factor_s),
        offset=float(offset_s),
        unit=unit,
        endianness=Endianness.MOTOROLA if motorola else Endianness.INTEL,
        multiplexor=multiplexor,
        multiplex_ids=multiplex_ids,
    )


def parse_text(text: str) -> DbcDatabase:
    """DBC 텍스트를 파싱해 `DbcDatabase`를 반환한다."""
    db = DbcDatabase()
    current: DbMessage | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        m = _VERSION_RE.match(line)
        if m:
            db.version = m.group(1)
            continue

        m = _BU_RE.match(line)
        if m:
            db.nodes = m.group(1).split()
            continue

        if line.startswith("NS_") or line.startswith("BS_"):
            continue  # 심볼/비트타이밍은 건너뜀

        m = _BO_RE.match(line)
        if m:
            raw_id = int(m.group(1))
            extended = bool(raw_id & _EXTENDED_ID_FLAG)
            current = DbMessage(
                name=m.group(2),
                code=raw_id & _EXTENDED_ID_MASK,
                length=int(m.group(3)),
                transmitter=m.group(4),
                extended=extended,
            )
            db.add_message(current)
            continue

        if line.lstrip().startswith("SG_"):
            if current is None:
                continue
            sig = _parse_signal(raw_line, current.length)
            if sig is not None:
                current.signals.append(sig)
            continue

        m = _VAL_RE.match(line)
        if m:
            msg_id = int(m.group(1)) & _EXTENDED_ID_MASK
            msg = db.get_by_id(msg_id)
            if msg is not None:
                sig = msg.get_signal(m.group(2))
                if sig is not None:
                    sig.desc_values = [
                        (desc, int(val))
                        for val, desc in _VAL_PAIR_RE.findall(m.group(3))
                    ]
            continue

        m = _SIG_VALTYPE_RE.match(line)
        if m:
            msg_id = int(m.group(1)) & _EXTENDED_ID_MASK
            msg = db.get_by_id(msg_id)
            if msg is not None:
                sig = msg.get_signal(m.group(2))
                if sig is not None:
                    if m.group(3) == "1":
                        sig.signal_type = SignalValueType.FLOAT
                    elif m.group(3) == "2":
                        sig.signal_type = SignalValueType.DOUBLE
            continue

        m = _CM_SG_RE.match(line)
        if m:
            msg_id = int(m.group(1)) & _EXTENDED_ID_MASK
            msg = db.get_by_id(msg_id)
            if msg is not None:
                sig = msg.get_signal(m.group(2))
                if sig is not None:
                    sig.comment = m.group(3)
            continue

        m = _CM_BO_RE.match(line)
        if m:
            msg_id = int(m.group(1)) & _EXTENDED_ID_MASK
            msg = db.get_by_id(msg_id)
            if msg is not None:
                msg.comment = m.group(2)
            continue
        # BA_, EV_, BA_DEF_ 등은 무시

    return db


def parse_file(path: str) -> DbcDatabase:
    """DBC 파일을 파싱해 `DbcDatabase`를 반환한다."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return parse_text(f.read())
