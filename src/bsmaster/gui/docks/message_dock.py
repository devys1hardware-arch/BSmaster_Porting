"""메시지 윈도우 도크.

원본 BUSMASTER의 메시지 윈도우(수신 프레임 리스트)에 대응.
`MessageTableModel`을 `QTableView`로 보여준다.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from bsmaster.core.filters import CanFilter, Direction, FilterKind, FilterSet
from bsmaster.gui.models import MessageTableModel
from bsmaster.logconv.frames import LogFrame


class MessageDock(QDockWidget):
    """수신/송신 프레임 목록을 보여주는 도킹 패널 (ID 범위 필터 포함)."""

    def __init__(self, parent=None) -> None:
        super().__init__("메시지", parent)
        self.model = MessageTableModel(self)

        self.view = QTableView(self)
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setStretchLastSection(True)

        # 필터 바
        self.filter_check = QCheckBox("필터", self)
        self.filter_check.toggled.connect(self._apply_filter)
        self.from_edit = QLineEdit("0", self)
        self.from_edit.setPlaceholderText("From (16진)")
        self.from_edit.setMaximumWidth(80)
        self.from_edit.textChanged.connect(self._apply_filter)
        self.to_edit = QLineEdit("7FF", self)
        self.to_edit.setPlaceholderText("To (16진)")
        self.to_edit.setMaximumWidth(80)
        self.to_edit.textChanged.connect(self._apply_filter)
        self.dir_combo = QComboBox(self)
        self.dir_combo.addItems(["전체", "Rx", "Tx"])
        self.dir_combo.currentIndexChanged.connect(self._apply_filter)

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(self.filter_check)
        filter_bar.addWidget(self.from_edit)
        filter_bar.addWidget(self.to_edit)
        filter_bar.addWidget(self.dir_combo)
        filter_bar.addStretch(1)

        clear_btn = QPushButton("지우기", self)
        clear_btn.clicked.connect(self.clear)

        layout = QVBoxLayout()
        layout.addLayout(filter_bar)
        layout.addWidget(self.view)
        layout.addWidget(clear_btn)
        container = QWidget(self)
        container.setLayout(layout)
        self.setWidget(container)

    def _apply_filter(self) -> None:
        if not self.filter_check.isChecked():
            self.model.set_filter(None)
            return
        try:
            f_from = int(self.from_edit.text().strip(), 16)
            f_to = int(self.to_edit.text().strip(), 16)
        except ValueError:
            return
        dir_text = self.dir_combo.currentText()
        direction = {"Rx": Direction.RX, "Tx": Direction.TX}.get(
            dir_text, Direction.ALL)
        fs = FilterSet(name="dock", mode="pass", filters=[
            CanFilter(kind=FilterKind.ID_RANGE, id_from=f_from, id_to=f_to,
                      direction=direction),
        ])
        self.model.set_filter(fs)

    def add_frame(self, frame: LogFrame) -> None:
        self.model.append_frame(frame)
        self.view.scrollToBottom()

    def clear(self) -> None:
        self.model.clear()

    @property
    def frame_count(self) -> int:
        return self.model.rowCount()
