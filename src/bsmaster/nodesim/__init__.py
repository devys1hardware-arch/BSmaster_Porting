"""가상 노드 시뮬레이션 (Phase 8).

원본 `NodeSimEx/` (C 스크립팅 IDE)를 Python 네이티브로 재설계:
사용자는 `VirtualNode`를 상속받아 핸들러를 작성한다.

- `node.VirtualNode`: 노드 베이스 클래스
- `bus.VirtualBus`: 가상 시간 기반 스케줄러

예:
    class EngineNode(VirtualNode):
        def on_start(self):
            self.every(100, self.send_rpm)
        def send_rpm(self):
            self.send_can(0x100, bytes([0x58, 0x02]))

    bus = VirtualBus()
    bus.add_node(EngineNode("engine"))
    bus.run(1.0)  # 가상 시간 1초 시뮬레이션
"""

from bsmaster.nodesim.bus import VirtualBus
from bsmaster.nodesim.node import VirtualNode

__all__ = ["VirtualBus", "VirtualNode"]
