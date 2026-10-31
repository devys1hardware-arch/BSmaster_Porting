"""가상 버스: 노드 스케줄러 (Phase 8).

가상 시간 기반 결정적 시뮬레이션. `step(dt)`로 시간을 전진시키고,
만기가 된 타이머를 실행, 프레임을 노드들에 전달한다.
"""

from __future__ import annotations

from bsmaster.logconv.frames import LogFrame
from bsmaster.nodesim.node import VirtualNode


class VirtualBus:
    """가상 CAN 버스."""

    def __init__(self) -> None:
        self.nodes: list[VirtualNode] = []
        self.time: float = 0.0
        self.tx_log: list[tuple[float, str, LogFrame]] = []
        self._running = False

    def add_node(self, node: VirtualNode) -> VirtualNode:
        node._bus = self
        # 타이머 기준 시각을 현재로 맞춤
        for timer in node._timers:
            timer[2] = self.time + timer[0]
        self.nodes.append(node)
        return node

    def remove_node(self, node: VirtualNode) -> None:
        node._bus = None
        self.nodes.remove(node)

    def start(self) -> None:
        self._running = True
        for node in self.nodes:
            node.on_start()

    def stop(self) -> None:
        for node in self.nodes:
            node.on_stop()
        self._running = False

    def _emit(self, sender: VirtualNode, frame: LogFrame) -> None:
        frame.timestamp = self.time
        self.tx_log.append((self.time, sender.name, frame))
        for node in self.nodes:
            if node is not sender:
                node.on_frame(frame)

    def inject(self, frame: LogFrame) -> None:
        """외부 프레임을 버스에 주입 (모든 노드가 수신)."""
        frame.timestamp = self.time
        for node in self.nodes:
            node.on_frame(frame)

    def step(self, dt: float) -> None:
        """가상 시간을 dt만큼 전진."""
        self.time += dt
        for node in self.nodes:
            for timer in node._timers:
                period, callback, next_fire = timer
                while next_fire <= self.time:
                    callback()
                    next_fire += period
                timer[2] = next_fire

    def run(self, duration: float, dt: float = 0.001) -> None:
        """duration초 동안 시뮬레이션 실행."""
        self.start()
        try:
            steps = int(duration / dt)
            for _ in range(steps):
                self.step(dt)
        finally:
            self.stop()

    def frames_from(self, node_name: str) -> list[LogFrame]:
        """특정 노드가 송신한 프레임 목록."""
        return [f for _, name, f in self.tx_log if name == node_name]
