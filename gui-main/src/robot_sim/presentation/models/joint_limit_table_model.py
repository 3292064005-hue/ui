from __future__ import annotations
from robot_sim.model.dh_row import DHRow

try:
    from PySide6.QtCore import QAbstractTableModel, Qt
except Exception:  # pragma: no cover
    QAbstractTableModel = object  # type: ignore
    Qt = object  # type: ignore


class JointLimitTableModel(QAbstractTableModel):  # pragma: no cover - GUI shell
    HEADERS = ["joint", "q_min", "q_max"]

    def __init__(self, rows: list[DHRow] | None = None):
        super().__init__()
        self.rows = list(rows or [])

    def set_rows(self, rows: list[DHRow]) -> None:
        if hasattr(self, "beginResetModel"):
            self.beginResetModel()
        self.rows = list(rows)
        if hasattr(self, "endResetModel"):
            self.endResetModel()

    def rowCount(self, parent=None):
        return len(self.rows)

    def columnCount(self, parent=None):
        return 3

    def data(self, index, role=None):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            row = self.rows[index.row()]
            values = [index.row(), row.q_min, row.q_max]
            return values[index.column()]
        return None

    def headerData(self, section, orientation, role=None):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None
