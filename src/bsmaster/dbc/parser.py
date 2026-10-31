"""DBC 파일 파서. (Phase 2에서 구현 예정)

원본 BUSMASTER의 DBC 처리(`Format Converter/DBC2DBFConverter`)에 대응한다.
목표 API (초안):

- `parse_file(path) -> Database`: DBC 파일을 읽어 메시지/시그널 DB로 변환
- `Database.messages`: 메시지 목록
- `Message.signals`: 시그널 목록, `encode()` / `decode()` 제공
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Signal:
    """DBC 시그널 정의 (초안)."""

    name: str = ""
    start_bit: int = 0
    length: int = 0
    factor: float = 1.0
    offset: float = 0.0


@dataclass
class Message:
    """DBC 메시지 정의 (초안)."""

    msg_id: int = 0
    name: str = ""
    dlc: int = 8
    signals: list[Signal] = field(default_factory=list)


@dataclass
class Database:
    """DBC 데이터베이스 (초안)."""

    messages: list[Message] = field(default_factory=list)


def parse_file(path: str) -> Database:
    """DBC 파일을 파싱한다. (Phase 2에서 구현)"""
    raise NotImplementedError("Phase 2에서 구현 예정")
