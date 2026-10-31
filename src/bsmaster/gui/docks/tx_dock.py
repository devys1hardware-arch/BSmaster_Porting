"""Tx 전송 패널 도크.

원본 BUSMASTER의 Tx 윈도우(`CTxWindow`)에 대응.
ID/DLC/데이터를 입력받아 `LogFrame(direction="Tx")`을 만든다.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from bsmaster.logconv.frames import LogFrame


class TxDock(QDockWidget):
    """CAN 프레임 전송 패널."""

    frame_created = Signal(LogFrame)

    def __init__(self, parent=None) -> None:
        super().__init__("전송", parent)

        self.id_edit = QLineEdit("100", self)
        self.id_edit.setPlaceholderText("16진수 ID (예: 100)")

        self.ext_check = QCheckBox("확장 ID (29비트)", self)

        self.dlc_spin = QSpinBox(self)
        self.dlc_spin.setRange(0, 8)
        self.dlc_spin.setValue(8)

        self.data_edit = QLineEdit("01 02 03 04 05 06 07 08", self)
        self.data_edit.setPlaceholderText("16진수 바이트 (공백 구분)")

        send_btn = QPushButton("전송", self)
        send_btn.clicked.connect(self._on_send)

        form = QFormLayout()
        form.addRow("ID", self.id_edit)
        form.addRow("", self.ext_check)
        form.addRow("DLC", self.dlc_spin)
        form.addRow("데이터", self.data_edit)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(send_btn)
        layout.addStretch(1)
        container = QWidget(self)
        container.setLayout(layout)
        self.setWidget(container)

    def build_frame(self, timestamp: float = 0.0) -> LogFrame:
        """입력값으로 `LogFrame`을 만든다. 값이 잘못되면 ValueError."""
        try:
            msg_id = int(self.id_edit.text().strip(), 16)
        except ValueError:
            raise ValueError("ID는 16진수로 입력하세요")
        extended = self.ext_check.isChecked()
        if not extended and msg_id > 0x7FF:
            raise ValueError("11비트 ID 범위를 초과했습니다")
        if extended and msg_id > 0x1FFFFFFF:
            raise ValueError("29비트 ID 범위를 초과했습니다")
        try:
            data = bytes(int(b, 16) for b in self.data_edit.text().split())
        except ValueError:
            raise ValueError("데이터는 16진수 바이트로 입력하세요")
        dlc = self.dlc_spin.value()
        data = data[:dlc].ljust(dlc, b"\x00")
        return LogFrame(
            timestamp=timestamp,
            channel=1,
            msg_id=msg_id,
            extended=extended,
            direction="Tx",
            data=data,
        )

    def _on_send(self) -> None:
        try:
            frame = self.build_frame()
        except ValueError as e:
            self.parent().statusBar().showMessage(str(e), 3000)
            return
        self.frame_created.emit(frame)
