"""로깅 파이프라인 테스트 (Phase 9)."""

from bsmaster.core.filters import CanFilter, FilterKind, FilterSet
from bsmaster.core.logging import Logger, LogInfo, LogTrigger, LogTriggerState
from bsmaster.logconv.asc import read_asc
from bsmaster.logconv.blf import read_blf
from bsmaster.logconv.frames import LogFrame


def _f(msg_id, ts=0.0):
    return LogFrame(timestamp=ts, msg_id=msg_id, data=b"\x01")


def test_trigger_none_logs_all(tmp_path):
    info = LogInfo(file_path=str(tmp_path / "t.asc"))
    with Logger(info) as log:
        log.process(_f(0x100))
        log.process(_f(0x200))
        assert log.buffered == 2
    assert [f.msg_id for f in read_asc(str(tmp_path / "t.asc"))] == [0x100, 0x200]


def test_trigger_start(tmp_path):
    trig = LogTrigger(LogTriggerState.START, start_id=0x200)
    info = LogInfo(file_path=str(tmp_path / "t.asc"), trigger=trig)
    log = Logger(info)
    log.process(_f(0x100))
    assert not log.active and log.buffered == 0
    log.process(_f(0x200))  # 시작 트리거 (이 프레임부터 기록)
    assert log.active and log.buffered == 1
    log.process(_f(0x300))
    assert log.buffered == 2
    log.save()
    assert [f.msg_id for f in read_asc(str(tmp_path / "t.asc"))] == [0x200, 0x300]


def test_trigger_stop():
    trig = LogTrigger(LogTriggerState.STOP, stop_id=0x200)
    info = LogInfo(trigger=trig)
    log = Logger(info)
    assert log.active
    log.process(_f(0x100))
    log.process(_f(0x200))  # 정지 트리거 (이 프레임까지 기록 후 정지)
    assert not log.active and log.buffered == 2
    log.process(_f(0x300))
    assert log.buffered == 2


def test_trigger_both_shuttle():
    trig = LogTrigger(LogTriggerState.BOTH, start_id=0x100, stop_id=0x200)
    info = LogInfo(trigger=trig)
    log = Logger(info)
    assert not log.active
    log.process(_f(0x100))
    assert log.active
    log.process(_f(0x150))
    log.process(_f(0x200))
    assert not log.active
    assert log.buffered == 3
    log.process(_f(0x100))  # 다시 시작
    assert log.active and log.buffered == 4


def test_filter_applied():
    fs = FilterSet(mode="pass", filters=[
        CanFilter(kind=FilterKind.SINGLE_ID, id_from=0x100)])
    info = LogInfo(filter=fs)
    log = Logger(info)
    log.process(_f(0x100))
    log.process(_f(0x200))
    assert log.buffered == 1


def test_disabled_logs_nothing():
    info = LogInfo(enabled=False)
    log = Logger(info)
    log.process(_f(0x100))
    assert log.buffered == 0


def test_blf_save_roundtrip(tmp_path):
    p = tmp_path / "t.blf"
    info = LogInfo(file_path=str(p), format="blf")
    with Logger(info) as log:
        log.process(_f(0x100, ts=1.0))
        log.process(_f(0x18DAF110, ts=2.0))
    frames = read_blf(str(p))
    assert [f.msg_id for f in frames] == [0x100, 0x18DAF110]


def test_append_mode(tmp_path):
    p = tmp_path / "t.asc"
    info = LogInfo(file_path=str(p), file_mode="append")
    with Logger(info) as log:
        log.process(_f(0x100))
    with Logger(info) as log:
        log.process(_f(0x200))
    assert [f.msg_id for f in read_asc(str(p))] == [0x100, 0x200]


def test_bus_to_log_end_to_end(tmp_path):
    # 가상 버스 → 로거 → ASC 파일 전체 흐름
    from bsmaster.nodesim import VirtualBus, VirtualNode

    class TxNode(VirtualNode):
        def on_start(self):
            self.every(100, lambda: self.send_can(0x100, b"\x01"))

    bus = VirtualBus()
    bus.add_node(TxNode("ecu"))
    p = tmp_path / "sim.asc"
    with Logger(LogInfo(file_path=str(p))) as log:
        bus.start()
        for _ in range(10):
            bus.step(0.1)
            for _, _, frame in bus.tx_log[log.buffered:]:
                log.process(frame)
        bus.stop()
    assert len(read_asc(str(p))) == 10
