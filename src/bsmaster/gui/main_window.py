"""PySide6 메인 윈도우.

BUSMASTER 원본의 MFC 메인 프레임(`Sources/BUSMASTER/Application/`)에
대응하는 Qt 메인 윈도우 뼈대이다. 도킹/메뉴 구조는 Phase 4에서 확장한다.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QStatusBar,
)


class MainWindow(QMainWindow):
    """BSmaster 메인 윈도우."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BSmaster")
        self.resize(1280, 800)

        self._build_menus()
        self._build_central()
        self._build_statusbar()

    def _build_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("파일(&F)")
        file_menu.addAction("종료(&X)", self.close)

        view_menu = menubar.addMenu("보기(&V)")
        view_menu.addAction("메시지 창", self._show_placeholder)

        help_menu = menubar.addMenu("도움말(&H)")
        about_action = help_menu.addAction("BSmaster 정보")
        about_action.triggered.connect(self._show_about)

    def _build_central(self) -> None:
        label = QLabel("BSmaster — BUSMASTER Python 포팅 (Phase 0 뼈대)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)

    def _build_statusbar(self) -> None:
        statusbar = QStatusBar(self)
        statusbar.showMessage("준비")
        self.setStatusBar(statusbar)

    def _show_placeholder(self) -> None:
        self.statusBar().showMessage("메시지 창: Phase 4에서 구현 예정", 3000)

    def _show_about(self) -> None:
        self.statusBar().showMessage(
            "BSmaster 0.1.0 — BUSMASTER Python/PySide6 포팅", 5000
        )


def run() -> int:
    """GUI를 실행하고 종료 코드를 반환한다."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
