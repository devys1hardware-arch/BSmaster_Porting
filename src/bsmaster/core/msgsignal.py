"""메시지/시그널 데이터베이스 타입과 시그널 인코딩 로직.

BUSMASTER 원본을 포팅:
- `DataTypes/MsgSignal_Datatypes.h`:
  `sSIGNALS` → `DbSignal`, `sMESSAGE` → `DbMessage`,
  `SMSGENTRY` 연결 리스트 → `MessageDatabase`,
  `sINTERPRETSIGNALINFO` → `InterpretedSignal`,
  `eWAVEFORMTYPE` → `WaveformType`, `eTIMINGS` → `TimingType`
- `Kernel/ProtocolDefinitions/CommonDefines.h`:
  `eEndianess` → `Endianness` (eMotorola=0, eIntel=1 순서 유지)
- `Format Converter/DBC2DBFConverterLibrary/DBFSignal.h`:
  `SIG_TYPE` → `SignalValueType`
- `sSIGNALS::vSetSignalValue()` → `encode_signal()`
- `sSIGNALS::un64GetBitMask()` → `signal_bitmask()`

비트 배치 규칙은 원본 C++과 동일하다:
- Intel: `shift = (start_byte - 1) * 8 + start_bit`
- Motorola: `shift = 64 - (start_byte * 8 - start_bit)` 후 8바이트 순서 반전
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterator, Optional

_MASK64 = 0xFFFFFFFFFFFFFFFF
_DATA_LEN = 8  # vSetSignalValue가 다루는 데이터 버퍼 크기 (UCHAR aucData[8])


class Endianness(IntEnum):
    """원본 `eEndianess`. Motorola=0, Intel=1 순서를 유지한다."""

    MOTOROLA = 0
    INTEL = 1


class SignalValueType(IntEnum):
    """원본 `DBFSignal.h`의 `SIG_TYPE`. 문자 코드값을 유지한다."""

    BOOL = ord("B")
    INT = ord("I")
    UINT = ord("U")
    FLOAT = ord("F")
    DOUBLE = ord("D")
    INT64 = ord("X")
    UINT64 = ord("Y")

    @property
    def is_signed(self) -> bool:
        return self in (
            SignalValueType.INT,
            SignalValueType.INT64,
        )


class WaveformType(IntEnum):
    """원본 `eWAVEFORMTYPE`."""

    NONE = 0
    SINE = 1
    TRIANGLE = 2
    COS = 3
    SAWTOOTH = 4


class TimingType(IntEnum):
    """원본 `eTIMINGS`."""

    UNDEFINED = 0
    CYCLIC = 1
    EVENT_CONTROLLED = 2
    REQUEST_CONTROLLED = 3
    RELATIVELY_SCHEDULED = 4
    ABSOLUTELY_SCHEDULED = 5
    IDENTIFIER = 6


@dataclass
class DbSignal:
    """시그널 정의. 원본 `sSIGNALS`에 대응한다.

    `start_byte`는 1부터 시작하는 바이트 번호 (원본 `m_unStartByte`),
    `start_bit`는 바이트 내 비트 번호 (원본 `m_byStartBit`)이다.
    연결 리스트(`m_psNextSignalList`) 대신 Python 리스트를 사용한다.
    """

    name: str = ""
    start_byte: int = 1
    start_bit: int = 0
    length: int = 8
    signal_type: SignalValueType = SignalValueType.UINT
    min_value: int = 0
    max_value: int = 0
    factor: float = 1.0
    offset: float = 0.0
    unit: str = ""
    endianness: Endianness = Endianness.INTEL
    desc_values: list[tuple[str, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 1 <= self.start_byte <= 8:
            raise ValueError(f"start_byte out of range: {self.start_byte}")
        if not 0 <= self.start_bit <= 7:
            raise ValueError(f"start_bit out of range: {self.start_bit}")
        if not 1 <= self.length <= 64:
            raise ValueError(f"length out of range: {self.length}")


@dataclass
class DbMessage:
    """메시지 정의. 원본 `sMESSAGE`에 대응한다."""

    name: str = ""
    code: int = 0  # m_unMessageCode (메시지 ID)
    channel: int = 0
    signals: list[DbSignal] = field(default_factory=list)
    length: int = 8  # m_unMessageLength (DLC)
    extended: bool = False  # m_bMessageFrameFormat
    data_format: Endianness = Endianness.INTEL  # m_nMsgDataFormat (1=Intel)

    def get_signal(self, name: str) -> Optional[DbSignal]:
        for sig in self.signals:
            if sig.name == name:
                return sig
        return None


class MessageDatabase:
    """메시지 데이터베이스. 원본 `SMSGENTRY` 연결 리스트 + `CMsgSignal`의
    ID 해시맵(`m_omMsgDetailsIDMap`)에 대응한다. Python에서는 dict를 쓴다."""

    def __init__(self) -> None:
        self._by_id: dict[int, DbMessage] = {}
        self._by_name: dict[str, DbMessage] = {}

    def add_message(self, message: DbMessage) -> None:
        """원본 `SMSGENTRY::bUpdateMsgList()`에 대응."""
        self._by_id[message.code] = message
        self._by_name[message.name] = message

    def get_by_id(self, code: int) -> Optional[DbMessage]:
        """원본 `SMSGENTRY::bGetMsgPtrFromMsgId()`에 대응."""
        return self._by_id.get(code)

    def get_by_name(self, name: str) -> Optional[DbMessage]:
        """원본 `CMsgSignal::psGetMessagePointer(name)`에 대응."""
        return self._by_name.get(name)

    def remove_by_id(self, code: int) -> bool:
        message = self._by_id.pop(code, None)
        if message is None:
            return False
        self._by_name.pop(message.name, None)
        return True

    def message_ids(self) -> list[int]:
        """원본 `CMsgSignal::unListGetMessageIDs()`에 대응."""
        return list(self._by_id.keys())

    def __len__(self) -> int:
        return len(self._by_id)

    def __iter__(self) -> Iterator[DbMessage]:
        return iter(self._by_id.values())


@dataclass
class InterpretedSignal:
    """시그널 해석 결과. 원본 `sINTERPRETSIGNALINFO`에 대응한다."""

    signal_name: str = ""
    raw_value: int = 0
    phys_value: float = 0.0
    desc_value: str = ""
    unit: str = ""
    sig_length: int = 0


def _reverse_bytes_64(value: int) -> int:
    """8바이트 순서를 뒤집는다. 원본 C++의 바이트 스왑 루프와 동일하다."""
    return int.from_bytes(value.to_bytes(8, "little"), "big")


def signal_bitmask(signal: DbSignal) -> int:
    """시그널이 차지하는 비트 마스크(64비트 정수).

    원본 `sSIGNALS::un64GetBitMask()` 포팅.
    """
    result = (1 << signal.length) - 1
    if signal.endianness == Endianness.INTEL:
        shift = (signal.start_byte - 1) * 8 + signal.start_bit
        result <<= shift
    else:
        shift = 64 - (signal.start_byte * 8 - signal.start_bit)
        result = (result << shift) & _MASK64
        result = _reverse_bytes_64(result)
    return result & _MASK64


def encode_signal(signal: DbSignal, data: bytearray, value: int) -> None:
    """데이터 버퍼에 시그널 값을 기록한다 (in-place).

    원본 `sSIGNALS::vSetSignalValue()` 포팅.
    `data`는 최소 8바이트의 bytearray이며, 앞 8바이트만 사용한다.
    값은 시그널 비트 길이로 마스킹된다.
    """
    if len(data) < _DATA_LEN:
        raise ValueError(f"data must be at least {_DATA_LEN} bytes")
    masked = value & ((1 << signal.length) - 1)
    if signal.endianness == Endianness.INTEL:
        shift = (signal.start_byte - 1) * 8 + signal.start_bit
        placed = masked << shift
    else:
        shift = 64 - (signal.start_byte * 8 - signal.start_bit)
        placed = _reverse_bytes_64((masked << shift) & _MASK64)
    target = int.from_bytes(bytes(data[:_DATA_LEN]), "little")
    target = (target & ~signal_bitmask(signal)) | placed
    data[:_DATA_LEN] = (target & _MASK64).to_bytes(_DATA_LEN, "little")


def decode_signal(signal: DbSignal, data: bytes) -> int:
    """데이터 버퍼에서 시그널의 raw 값을 읽는다. `encode_signal()`의 역함수."""
    if len(data) < _DATA_LEN:
        raise ValueError(f"data must be at least {_DATA_LEN} bytes")
    target = int.from_bytes(bytes(data[:_DATA_LEN]), "little")
    mask = signal_bitmask(signal)
    if signal.endianness == Endianness.INTEL:
        shift = (signal.start_byte - 1) * 8 + signal.start_bit
        return (target & mask) >> shift
    shift = 64 - (signal.start_byte * 8 - signal.start_bit)
    return (_reverse_bytes_64(target & mask) >> shift) & ((1 << signal.length) - 1)


def to_physical(signal: DbSignal, raw_value: int) -> float:
    """raw 값 → 물리값. `물리값 = raw × factor + offset`."""
    value = raw_value
    if signal.signal_type.is_signed:
        sign_bit = 1 << (signal.length - 1)
        if value & sign_bit:
            value -= 1 << signal.length
    return value * signal.factor + signal.offset


def to_raw(signal: DbSignal, physical: float) -> int:
    """물리값 → raw 값 (반올림)."""
    if signal.factor == 0:
        raise ValueError("factor must not be zero")
    return int(round((physical - signal.offset) / signal.factor))


def interpret_signal(signal: DbSignal, data: bytes) -> InterpretedSignal:
    """데이터 버퍼에서 시그널을 해석해 `InterpretedSignal`로 반환한다."""
    raw = decode_signal(signal, data)
    desc = ""
    for desc_name, desc_val in signal.desc_values:
        if desc_val == raw:
            desc = desc_name
            break
    return InterpretedSignal(
        signal_name=signal.name,
        raw_value=raw,
        phys_value=to_physical(signal, raw),
        desc_value=desc,
        unit=signal.unit,
        sig_length=signal.length,
    )
