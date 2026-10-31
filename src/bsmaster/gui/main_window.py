"""PySide6 메인 윈도우 (Phase 4).

BUSMASTER 원본의 MFC 메인 프레임(`Sources/BUSMASTER/Application/`)에
대응하는 Qt 메인 윈도우. 도킹 패널 3개(메시지/시그널/전송),
메뉴(DBC·로그 열기), 가상 시뮬레이션 타이머를 갖는다.
"""

from __future__ import annotations

import random
import sys
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
)

from bsmaster.gui.docks import GraphDock, MessageDock, SignalDock, TxDock
from bsmaster.logconv.asc import read_asc
from bsmaster.logconv.blf import read_blf
from bsmaster.logconv.frames import LogFrame


class MainWindow(QMainWindow):
    """BSmaster 메인 윈도우."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BSmaster")
        self.resize(1280, 800)

        self._sim_start: float = 0.0
        self._build_docks()
        self._build_menus()
        self._build_central()
        self._build_statusbar()
        self._build_sim_timer()

    # -- 구성 ---------------------------------------------------------

    def _build_docks(self) -> None:
        self.message_dock = MessageDock(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.message_dock)

        self.signal_dock = SignalDock(self)
        self.signal_dock._load_handler = self.open_dbc
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.signal_dock)

        self.tx_dock = TxDock(self)
        self.tx_dock.frame_created.connect(self._on_tx_frame)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.tx_dock)

        self.graph_dock = GraphDock(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.graph_dock)

    def _build_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("파일(&F)")
        file_menu.addAction("DBC 열기(&D)", self.open_dbc)
        file_menu.addAction("로그 열기(&L)...", self.open_log)
        file_menu.addSeparator()
        file_menu.addAction("종료(&X)", self.close)

        view_menu = menubar.addMenu("보기(&V)")
        view_menu.addAction(self.message_dock.toggleViewAction())
        view_menu.addAction(self.signal_dock.toggleViewAction())
        view_menu.addAction(self.tx_dock.toggleViewAction())
        view_menu.addAction(self.graph_dock.toggleViewAction())

        sim_menu = menubar.addMenu("시뮬레이션(&S)")
        self._sim_start_action = sim_menu.addAction("시작", self.start_simulation)
        self._sim_stop_action = sim_menu.addAction("정지", self.stop_simulation)
        self._sim_stop_action.setEnabled(False)

        help_menu = menubar.addMenu("도움말(&H)")
        help_menu.addAction("BSmaster 정보", self._show_about)

    def _build_central(self) -> None:
        label = QLabel(
            "BSmaster — BUSMASTER Python 포팅\n\n"
            "시뮬레이션 메뉴에서 가상 수신을 시작하거나\n"
            "파일 메뉴에서 DBC·로그를 열어 보세요."
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)

    def _build_statusbar(self) -> None:
        statusbar = QStatusBar(self)
        statusbar.showMessage("준비")
        self.setStatusBar(statusbar)

    def _build_sim_timer(self) -> None:
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(200)  # 5 Hz
        self._sim_timer.timeout.connect(self._on_sim_tick)

    # -- 파일 열기 -----------------------------------------------------

    def open_dbc(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "DBC 파일 열기", "", "DBC 파일 (*.dbc)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            self.signal_dock.load_dbc_text(text)
            from bsmaster.dbc.parser import parse_text
            self.graph_dock.set_db(parse_text(text))
            self.statusBar().showMessage(f"DBC 로드: {path}", 5000)
        except Exception as e:
            QMessageBox.warning(self, "DBC 열기 실패", str(e))

    def open_log(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "로그 파일 열기", "",
            "로그 파일 (*.asc *.blf);;ASC (*.asc);;BLF (*.blf)")
        if not path:
            return
        try:
            if path.lower().endswith(".blf"):
                frames = read_blf(path)
            else:
                frames = read_asc(path)
            for frame in frames:
                self._add_frame(frame)
            self.statusBar().showMessage(
                f"로그 로드: {len(frames)} 프레임", 5000)
        except Exception as e:
            QMessageBox.warning(self, "로그 열기 실패", str(e))

    # -- 프레임 흐름 ---------------------------------------------------

    def _add_frame(self, frame: LogFrame) -> None:
        self.message_dock.add_frame(frame)
        self.signal_dock.show_frame(frame)
        self.graph_dock.show_frame(frame)
        self.statusBar().showMessage(f"프레임: {self.message_dock.frame_count}개")

    def _on_tx_frame(self, frame: LogFrame) -> None:
        frame.timestamp = time.time() - self._sim_start if self._sim_start else 0.0
        self._add_frame(frame)

    # -- 시뮬레이션 ----------------------------------------------------

    def start_simulation(self) -> None:
        self._sim_start = time.time()
        self._sim_timer.start()
        self._sim_start_action.setEnabled(False)
        self._sim_stop_action.setEnabled(True)
        self.statusBar().showMessage("시뮬레이션 실행 중")

    def stop_simulation(self) -> None:
        self._sim_timer.stop()
        self._sim_start_action.setEnabled(True)
        self._sim_stop_action.setEnabled(False)
        self.statusBar().showMessage("시뮬레이션 정지")

    def _on_sim_tick(self) -> None:
        db = self.signal_dock.db
        if db is not None and len(db) > 0:
            msg = random.choice(list(db))
            msg_id, dlc = msg.code, msg.length
            extended = msg.extended
        else:
            msg_id = random.choice([0x100, 0x200, 0x18DAF110])
            dlc = 8
            extended = msg_id > 0x7FF
        frame = LogFrame(
            timestamp=time.time() - self._sim_start,
            channel=1,
            msg_id=msg_id,
            extended=extended,
            direction="Rx",
            data=bytes(random.getrandbits(8) for _ in range(dlc)),
        )
        self._add_frame(frame)

    def _show_about(self) -> None:
        self.statusBar().showMessage(
            "BSmaster 0.1.0 — BUSMASTER Python/PySide6 포팅", 5000)


def run() -> int:
    """GUI를 실행하고 종료 코드를 반환한다."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
