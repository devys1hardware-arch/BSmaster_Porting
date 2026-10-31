"""가상 노드 시뮬레이션 테스트 (Phase 8)."""

from bsmaster.core.msgsignal import decode_signal, to_physical
from bsmaster.dbc.parser import parse_text
from bsmaster.logconv.frames import LogFrame
from bsmaster.nodesim import VirtualBus, VirtualNode

TEST_DBC = """VERSION "nodesim test"
BU_: ECU
BO_ 256 EngineData: 8 Vector__XXX
 SG_ RPM : 0|16@1+ (0.125,0) [0|8000] "rpm" Vector__XXX
"""


class PeriodicNode(VirtualNode):
    def __init__(self, name=""):
        super().__init__(name)
        self.sent = 0

    def on_start(self):
        self.every(100, self.tick)

    def tick(self):
        self.send_can(0x100, bytes([self.sent & 0xFF]))
        self.sent += 1


class EchoNode(VirtualNode):
    def __init__(self, name=""):
        super().__init__(name)
        self.received = []

    def on_frame(self, frame):
        self.received.append(frame)


def test_periodic_tx():
    bus = VirtualBus()
    node = bus.add_node(PeriodicNode("ecu"))
    bus.run(1.0)
    frames = bus.frames_from("ecu")
    assert len(frames) == 10  # 100ms 주기 × 1초
    assert node.sent == 10
    # 타임스탬프가 가상 시간 기준
    assert frames[0].timestamp < frames[-1].timestamp


def test_node_to_node_delivery():
    bus = VirtualBus()
    bus.add_node(PeriodicNode("sender"))
    echo = bus.add_node(EchoNode("receiver"))
    bus.run(0.5)
    assert len(echo.received) == 5
    # 송신자는 자신의 프레임을 받지 않음
    assert all(f.direction == "Tx" for f in echo.received)


def test_inject_frame():
    bus = VirtualBus()
    echo = bus.add_node(EchoNode("receiver"))
    bus.start()
    bus.inject(LogFrame(msg_id=0x200, direction="Rx", data=b"\xAA"))
    bus.stop()
    assert len(echo.received) == 1
    assert echo.received[0].msg_id == 0x200


def test_send_signals_with_dbc():
    db = parse_text(TEST_DBC)
    msg = db.get_by_id(0x100)

    class DbcNode(VirtualNode):
        def on_start(self):
            self.send_signals(msg, {"RPM": 4000.0})

    bus = VirtualBus()
    bus.add_node(DbcNode("ecu"))
    bus.run(0.01)
    frames = bus.frames_from("ecu")
    assert len(frames) == 1
    sig = msg.get_signal("RPM")
    raw = decode_signal(sig, frames[0].data)
    assert to_physical(sig, raw) == 4000.0


def test_lifecycle():
    events = []

    class LifeNode(VirtualNode):
        def on_start(self):
            events.append("start")

        def on_stop(self):
            events.append("stop")

    bus = VirtualBus()
    bus.add_node(LifeNode())
    bus.run(0.01)
    assert events == ["start", "stop"]


def test_deterministic():
    def run_once():
        bus = VirtualBus()
        bus.add_node(PeriodicNode("ecu"))
        bus.run(0.35)
        return [(round(t, 6), f.msg_id) for t, _, f in bus.tx_log]

    assert run_once() == run_once()
