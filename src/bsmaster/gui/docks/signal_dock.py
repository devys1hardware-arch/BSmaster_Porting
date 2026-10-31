"""시그널 해석 도크 (Signal Watch).

DBC를 로드하면 메시지 목록을 보여주고, 들어오는 프레임의
시그널을 디코딩해 물리값으로 표시한다.
원본 BUSMASTER의 Signal Watch(`CSignalWatchDlg`)에 대응.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bsmaster.core.msgsignal import decode_signal, to_physical
from bsmaster.dbc.parser import DbcDatabase, parse_text
from bsmaster.logconv.frames import LogFrame


class SignalDock(QDockWidget):
    """DBC 시그널 해석 패널."""

    def __init__(self, parent=None) -> None:
        super().__init__("시그널", parent)
        self.db: DbcDatabase | None = None

        load_btn = QPushButton("DBC 열기", self)
        load_btn.clicked.connect(self._on_load_clicked)

        self.msg_combo = QComboBox(self)
        self.msg_combo.currentIndexChanged.connect(self._refresh_table)

        top = QHBoxLayout()
        top.addWidget(load_btn)
        top.addWidget(self.msg_combo, 1)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["시그널", "원시값", "물리값", "단위"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.table)
        container = QWidget(self)
        container.setLayout(layout)
        self.setWidget(container)

        self._load_handler = None  # 메인 윈도우가 QFileDialog 핸들러를 주입

    def _on_load_clicked(self) -> None:
        if self._load_handler is not None:
            self._load_handler()

    def load_dbc_text(self, text: str) -> None:
        self.db = parse_text(text)
        self.msg_combo.clear()
        for msg in self.db:
            self.msg_combo.addItem(f"{msg.code:X} {msg.name}", msg.code)
        self._refresh_table()

    def _refresh_table(self) -> None:
        self.table.setRowCount(0)
        msg = self._current_message()
        if msg is None:
            return
        self.table.setRowCount(len(msg.signals))
        for row, sig in enumerate(msg.signals):
            self.table.setItem(row, 0, QTableWidgetItem(sig.name))
            self.table.setItem(row, 1, QTableWidgetItem("-"))
            self.table.setItem(row, 2, QTableWidgetItem("-"))
            self.table.setItem(row, 3, QTableWidgetItem(sig.unit))

    def _current_message(self):
        if self.db is None:
            return None
        code = self.msg_combo.currentData()
        return self.db.get_by_id(code) if code is not None else None

    def show_frame(self, frame: LogFrame) -> None:
        """들어온 프레임을 현재 선택된 메시지의 시그널로 해석해 표시."""
        msg = self._current_message()
        if msg is None or frame.msg_id != msg.code:
            return
        data = frame.data
        for row, sig in enumerate(msg.signals):
            try:
                raw = decode_signal(sig, data)
                phys = to_physical(sig, raw)
            except Exception:
                continue
            self.table.setItem(row, 1, QTableWidgetItem(str(raw)))
            self.table.setItem(row, 2, QTableWidgetItem(f"{phys:g}"))
