"""메시지 윈도우 도크.

원본 BUSMASTER의 메시지 윈도우(수신 프레임 리스트)에 대응.
`MessageTableModel`을 `QTableView`로 보여준다.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDockWidget,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from bsmaster.gui.models import MessageTableModel
from bsmaster.logconv.frames import LogFrame


class MessageDock(QDockWidget):
    """수신/송신 프레임 목록을 보여주는 도킹 패널."""

    def __init__(self, parent=None) -> None:
        super().__init__("메시지", parent)
        self.model = MessageTableModel(self)

        self.view = QTableView(self)
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setStretchLastSection(True)

        clear_btn = QPushButton("지우기", self)
        clear_btn.clicked.connect(self.clear)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(clear_btn)
        container = QWidget(self)
        container.setLayout(layout)
        self.setWidget(container)

    def add_frame(self, frame: LogFrame) -> None:
        self.model.append_frame(frame)
        self.view.scrollToBottom()

    def clear(self) -> None:
        self.model.clear()

    @property
    def frame_count(self) -> int:
        return self.model.rowCount()
