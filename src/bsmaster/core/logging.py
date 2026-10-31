"""로깅 파이프라인 (Phase 9).

원본: `DataTypes/Log_Datatypes.h`의 `SLOGTRIGGER`/`SLOGINFO`,
`FrameProcessor/BaseLogObject.*`의 로깅 개념을 포팅.

- `LogTrigger`: 시작/정지 트리거 상태 머신
  (NONE/START/STOP/BOTH — 원본 `ELOGTRIGGERSTATE` 대응)
- `LogInfo`: 로그 블록 설정 (파일, 포맷, 모드, 트리거, 필터)
- `Logger`: 프레임 수신 → 트리거/필터 적용 → 버퍼링 → 파일 저장
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum

from bsmaster.core.filters import FilterSet
from bsmaster.logconv.asc import read_asc, write_asc
from bsmaster.logconv.blf import read_blf, write_blf
from bsmaster.logconv.frames import LogFrame


class LogTriggerState(Enum):
    """원본 `ELOGTRIGGERSTATE`에 대응."""

    NONE = 0
    START = 1
    STOP = 2
    BOTH = 3


@dataclass
class LogTrigger:
    """원본 `SLOGTRIGGER`에 대응."""

    trigger_type: LogTriggerState = LogTriggerState.NONE
    start_id: int = 0  # m_unStartID
    stop_id: int = 0  # m_unStopID

    def update(self, frame: LogFrame, active: bool) -> bool:
        """프레임 수신 후 로깅 활성 상태 반환."""
        t = self.trigger_type
        if t == LogTriggerState.NONE:
            return active
        if t == LogTriggerState.START:
            return True if frame.msg_id == self.start_id else active
        if t == LogTriggerState.STOP:
            return False if frame.msg_id == self.stop_id else active
        # BOTH: 시작 ID에서 켜고, 정지 ID에서 끄는 셔틀
        if frame.msg_id == self.start_id:
            return True
        if frame.msg_id == self.stop_id:
            return False
        return active


@dataclass
class LogInfo:
    """원본 `SLOGINFO`의 핵심 필드에 대응."""

    file_path: str = ""
    format: str = "asc"  # "asc" | "blf"
    file_mode: str = "overwrite"  # "overwrite" | "append"
    enabled: bool = True  # m_bEnabled
    trigger: LogTrigger = field(default_factory=LogTrigger)
    filter: FilterSet | None = None


class Logger:
    """로그 블록. `process()`로 프레임을 받아 트리거·필터 후 버퍼링하고,
    `save()`(또는 컨텍스트 종료) 시 파일에 기록한다."""

    def __init__(self, info: LogInfo) -> None:
        self.info = info
        # NONE/STOP 트리거는 시작부터 활성, START/BOTH는 트리거 대기
        self._active = info.trigger.trigger_type in (
            LogTriggerState.NONE, LogTriggerState.STOP)
        self._frames: list[LogFrame] = []

    def process(self, frame: LogFrame) -> None:
        if not self.info.enabled:
            return
        was_active = self._active
        self._active = self.info.trigger.update(frame, was_active)
        # 시작/정지 경계 프레임 자체도 기록한다
        if self._active or was_active:
            filt = self.info.filter
            if filt is None or filt.passes(frame):
                self._frames.append(frame)

    @property
    def active(self) -> bool:
        return self._active

    @property
    def buffered(self) -> int:
        return len(self._frames)

    def save(self) -> None:
        if not self.info.file_path:
            raise ValueError("로그 파일 경로가 없습니다")
        fmt = self.info.format.lower()
        if fmt not in ("asc", "blf"):
            raise ValueError(f"지원하지 않는 포맷: {fmt}")
        frames = list(self._frames)
        if self.info.file_mode == "append" and os.path.exists(self.info.file_path):
            frames = self._read_existing(fmt) + frames
        if fmt == "asc":
            write_asc(self.info.file_path, frames)
        else:
            write_blf(self.info.file_path, frames)
        self._frames.clear()

    def _read_existing(self, fmt: str) -> list[LogFrame]:
        try:
            return read_asc(self.info.file_path) if fmt == "asc" \
                else read_blf(self.info.file_path)
        except Exception:
            return []

    def __enter__(self) -> "Logger":
        return self

    def __exit__(self, *exc) -> None:
        self.save()
