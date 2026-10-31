"""시그널 그래프 도크 (Phase 10).

원본 BUSMASTER의 `SigGrphWnd/` (시그널 그래프 윈도우)에 대응.
외부 의존성 없이 QPainter로 직접 그린다.

- `SignalSeries`: 시그널 하나분의 (시간, 값) 샘플 버퍼
- `SignalPlot`: QPainter 기반 플롯 위젯 (격자 + 다중 시그널 폴리라인)
- `GraphDock`: DBC 시그널 선택 + 들어오는 프레임 실시간 플로팅
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bsmaster.core.msgsignal import decode_signal, to_physical
from bsmaster.dbc.parser import DbcDatabase
from bsmaster.logconv.frames import LogFrame

PALETTE = ["#e74c3c", "#2980b9", "#27ae60", "#8e44ad",
           "#e67e22", "#16a085", "#2c3e50", "#d35400"]
MAX_SAMPLES = 10000


class SignalSeries:
    """시그널 하나의 샘플 버퍼."""

    def __init__(self, name: str, color: str, max_samples: int = MAX_SAMPLES) -> None:
        self.name = name
        self.color = color
        self.max_samples = max_samples
        self.samples: list[tuple[float, float]] = []

    def add(self, timestamp: float, value: float) -> None:
        self.samples.append((timestamp, value))
        if len(self.samples) > self.max_samples:
            del self.samples[:len(self.samples) - self.max_samples]

    def y_range(self) -> tuple[float, float]:
        if not self.samples:
            return (0.0, 1.0)
        vals = [v for _, v in self.samples]
        lo, hi = min(vals), max(vals)
        if lo == hi:
            lo -= 1.0
            hi += 1.0
        pad = (hi - lo) * 0.1
        return (lo - pad, hi + pad)

    def clear(self) -> None:
        self.samples.clear()


class SignalPlot(QWidget):
    """QPainter 기반 시그널 플롯."""

    def __init__(self, parent=None, window_sec: float = 30.0) -> None:
        super().__init__(parent)
        self._series: list[SignalSeries] = []
        self.window_sec = window_sec
        self.setMinimumHeight(150)

    def set_series(self, series: list[SignalSeries]) -> None:
        self._series = series
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        if not self._series or not any(s.samples for s in self._series):
            painter.setPen(QColor("#999999"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "시그널을 추가하세요")
            return

        all_t = [t for s in self._series for t, _ in s.samples]
        t_max = max(all_t)
        t_min = max(t_max - self.window_sec, min(all_t))
        y_lo = min(s.y_range()[0] for s in self._series if s.samples)
        y_hi = max(s.y_range()[1] for s in self._series if s.samples)

        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 50, 10, 10, 22
        pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
        if pw <= 0 or ph <= 0:
            return

        def x_of(t: float) -> float:
            return pad_l + (0 if t_max == t_min else (t - t_min) / (t_max - t_min) * pw)

        def y_of(v: float) -> float:
            return pad_t + (0 if y_hi == y_lo else (1 - (v - y_lo) / (y_hi - y_lo)) * ph)

        # 격자
        painter.setPen(QPen(QColor("#dddddd")))
        for i in range(1, 4):
            y = pad_t + ph * i / 4
            painter.drawLine(int(pad_l), int(y), int(pad_l + pw), int(y))

        # 축 라벨
        painter.setPen(QColor("#666666"))
        painter.drawText(4, int(pad_t + 10), f"{y_hi:.2g}")
        painter.drawText(4, int(pad_t + ph), f"{y_lo:.2g}")
        painter.drawText(int(pad_l), h - 6, f"{t_min:.1f}s")
        painter.drawText(int(pad_l + pw - 40), h - 6, f"{t_max:.1f}s")

        # 시그널 폴리라인
        for series in self._series:
            pts = [(x_of(t), y_of(v)) for t, v in series.samples if t >= t_min]
            if len(pts) < 2:
                continue
            painter.setPen(QPen(QColor(series.color), 2))
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 범례
        lx = pad_l + 6
        for series in self._series:
            painter.setPen(QPen(QColor(series.color), 3))
            painter.drawLine(lx, 14, lx + 18, 14)
            painter.setPen(QColor("#333333"))
            painter.drawText(lx + 22, 18, series.name)
            lx += 22 + painter.fontMetrics().horizontalAdvance(series.name) + 16


class GraphDock(QDockWidget):
    """시그널 그래프 도킹 패널."""

    def __init__(self, parent=None) -> None:
        super().__init__("그래프", parent)
        self._db: DbcDatabase | None = None
        self._tracked: list[tuple[int, str]] = []  # (msg_id, signal_name)
        self._series: dict[tuple[int, str], SignalSeries] = {}
        self._color_idx = 0

        self.msg_combo = QComboBox(self)
        self.sig_combo = QComboBox(self)
        self.msg_combo.currentIndexChanged.connect(self._refresh_sig_combo)
        add_btn = QPushButton("추가", self)
        add_btn.clicked.connect(self._on_add)
        clear_btn = QPushButton("지우기", self)
        clear_btn.clicked.connect(self.clear)

        top = QHBoxLayout()
        top.addWidget(self.msg_combo, 1)
        top.addWidget(self.sig_combo, 1)
        top.addWidget(add_btn)
        top.addWidget(clear_btn)

        self.plot = SignalPlot(self)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.plot, 1)
        container = QWidget(self)
        container.setLayout(layout)
        self.setWidget(container)

    def set_db(self, db: DbcDatabase | None) -> None:
        self._db = db
        self.msg_combo.clear()
        if db is not None:
            for msg in db:
                self.msg_combo.addItem(f"{msg.code:X} {msg.name}", msg.code)
        self._refresh_sig_combo()

    def _refresh_sig_combo(self) -> None:
        self.sig_combo.clear()
        msg = self._current_message()
        if msg is not None:
            for sig in msg.signals:
                self.sig_combo.addItem(sig.name)

    def _current_message(self):
        if self._db is None:
            return None
        code = self.msg_combo.currentData()
        return self._db.get_by_id(code) if code is not None else None

    def _on_add(self) -> None:
        msg = self._current_message()
        name = self.sig_combo.currentText()
        if msg is None or not name:
            return
        self.track_signal(msg.code, name)

    def track_signal(self, msg_id: int, signal_name: str) -> None:
        key = (msg_id, signal_name)
        if key in self._series:
            return
        color = PALETTE[self._color_idx % len(PALETTE)]
        self._color_idx += 1
        self._series[key] = SignalSeries(f"{msg_id:X}:{signal_name}", color)
        self._tracked.append(key)
        self.plot.set_series(list(self._series.values()))

    def show_frame(self, frame: LogFrame) -> None:
        if self._db is None:
            return
        for key in self._tracked:
            msg_id, sig_name = key
            if frame.msg_id != msg_id:
                continue
            msg = self._db.get_by_id(msg_id)
            if msg is None:
                continue
            sig = msg.get_signal(sig_name)
            if sig is None:
                continue
            try:
                raw = decode_signal(sig, frame.data)
                self._series[key].add(frame.timestamp, to_physical(sig, raw))
            except Exception:
                continue
        self.plot.update()

    def clear(self) -> None:
        for s in self._series.values():
            s.clear()
        self.plot.update()
