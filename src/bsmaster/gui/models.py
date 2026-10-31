"""Qt 모델: 메시지 윈도우용 테이블 모델.

원본 BUSMASTER의 메시지 윈도우(`CMessageWindow`) 리스트를
`QAbstractTableModel`로 포팅. 데이터는 `LogFrame` 리스트.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from bsmaster.logconv.frames import LogFrame

COLUMNS = ["시간", "Tx/Rx", "채널", "ID", "DLC", "데이터"]


class MessageTableModel(QAbstractTableModel):
    """로그 프레임 테이블 모델."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._frames: list[LogFrame] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._frames)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        frame = self._frames[index.row()]
        col = index.column()
        if col == 0:
            return f"{frame.timestamp:.6f}"
        if col == 1:
            return frame.direction
        if col == 2:
            return str(frame.channel)
        if col == 3:
            return f"{frame.msg_id:X}"
        if col == 4:
            return str(len(frame.data))
        if col == 5:
            return " ".join(f"{b:02X}" for b in frame.data)
        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return COLUMNS[section]
        return None

    def append_frame(self, frame: LogFrame) -> None:
        row = len(self._frames)
        self.beginInsertRows(QModelIndex(), row, row)
        self._frames.append(frame)
        self.endInsertRows()

    def clear(self) -> None:
        self.beginResetModel()
        self._frames.clear()
        self.endResetModel()

    @property
    def frames(self) -> list[LogFrame]:
        return list(self._frames)
