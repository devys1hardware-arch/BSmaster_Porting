"""GUI 테스트 (오프스크린)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication

from bsmaster.gui.docks import MessageDock, SignalDock, TxDock
from bsmaster.gui.main_window import MainWindow
from bsmaster.gui.models import COLUMNS, MessageTableModel
from bsmaster.logconv.frames import LogFrame

TEST_DBC = """VERSION "gui test"

BU_: ECU

BO_ 256 EngineData: 8 Vector__XXX
 SG_ RPM : 0|16@1+ (0.125,0) [0|8000] "rpm" Vector__XXX
 SG_ Temp : 16|8@1- (1,-40) [-40|215] "degC" Vector__XXX
"""


@pytest.fixture(scope="session")
def app():
    return QApplication([])


def test_message_model(app):
    model = MessageTableModel()
    assert model.columnCount() == len(COLUMNS)
    assert model.rowCount() == 0
    model.append_frame(LogFrame(timestamp=1.0, channel=1, msg_id=0x100,
                                direction="Rx", data=bytes([1, 2, 3])))
    assert model.rowCount() == 1
    idx = model.index(0, 3)
    assert model.data(idx) == "100"
    assert model.data(model.index(0, 5)) == "01 02 03"
    assert model.data(model.index(0, 1)) == "Rx"
    model.clear()
    assert model.rowCount() == 0


def test_main_window_docks(app):
    win = MainWindow()
    assert isinstance(win.message_dock, MessageDock)
    assert isinstance(win.signal_dock, SignalDock)
    assert isinstance(win.tx_dock, TxDock)
    assert win.windowTitle() == "BSmaster"


def test_tx_dock_build_frame(app):
    dock = TxDock()
    dock.id_edit.setText("1A0")
    dock.dlc_spin.setValue(2)
    dock.data_edit.setText("DE AD BE EF")
    frame = dock.build_frame(timestamp=3.0)
    assert frame.msg_id == 0x1A0
    assert frame.direction == "Tx"
    assert frame.data == bytes([0xDE, 0xAD])
    assert frame.timestamp == pytest.approx(3.0)


def test_tx_dock_bad_input(app):
    dock = TxDock()
    dock.id_edit.setText("ZZZ")
    with pytest.raises(ValueError):
        dock.build_frame()


def test_tx_dock_signal(app):
    dock = TxDock()
    received = []
    dock.frame_created.connect(received.append)
    dock.id_edit.setText("100")
    dock._on_send()
    assert len(received) == 1
    assert received[0].msg_id == 0x100


def test_signal_dock_interpret(app):
    dock = SignalDock()
    dock.load_dbc_text(TEST_DBC)
    assert dock.msg_combo.count() == 1

    # RPM = 600 → 0x0258 리틀엔디안, Temp = -40+60=20 → raw 60
    data = bytes([0x58, 0x02, 60] + [0] * 5)
    dock.show_frame(LogFrame(timestamp=0.0, channel=1, msg_id=0x100,
                             direction="Rx", data=data))
    assert dock.table.item(0, 1).text() == "600"     # 원시값
    assert dock.table.item(0, 2).text() == "75"      # 600 * 0.125
    assert dock.table.item(1, 2).text() == "20"      # (60-40)


def test_sim_tick_adds_frame(app):
    win = MainWindow()
    assert win.message_dock.frame_count == 0
    win.start_simulation()
    win._on_sim_tick()
    win._on_sim_tick()
    win.stop_simulation()
    assert win.message_dock.frame_count == 2
