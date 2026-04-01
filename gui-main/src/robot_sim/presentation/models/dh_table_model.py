from __future__ import annotations
from typing import Any
from robot_sim.model.dh_row import DHRow
from robot_sim.domain.enums import JointType

try:
    from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
except Exception:  # pragma: no cover
    QAbstractTableModel = object  # type: ignore
    Qt = object  # type: ignore
    QModelIndex = object  # type: ignore


class DHTableModel(QAbstractTableModel):  # pragma: no cover - GUI shell
    HEADERS = ["a", "alpha", "d", "theta_offset", "type", "q_min", "q_max"]

    def __init__(self, rows: list[DHRow] | None = None):
        super().__init__()
        self.rows: list[DHRow] = list(rows or [])

    def set_rows(self, rows: list[DHRow]) -> None:
        if hasattr(self, "beginResetModel"):
            self.beginResetModel()
        self.rows = list(rows)
        if hasattr(self, "endResetModel"):
            self.endResetModel()

    def to_rows(self) -> tuple[DHRow, ...]:
        return tuple(self.rows)

    def rowCount(self, parent=None):
        return len(self.rows)

    def columnCount(self, parent=None):
        return len(self.HEADERS)

    def _value_at(self, row: DHRow, column: int) -> Any:
        mapping = [
            row.a,
            row.alpha,
            row.d,
            row.theta_offset,
            row.joint_type.value,
            row.q_min,
            row.q_max,
        ]
        return mapping[column]

    def data(self, index, role=None):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            return self._value_at(self.rows[index.row()], index.column())
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index, value, role=None):
        if role != Qt.EditRole or not index.isValid():
            return False
        row = self.rows[index.row()]
        col = index.column()
        try:
            if col == 4:
                joint_type = JointType(str(value))
                new_row = DHRow(row.a, row.alpha, row.d, row.theta_offset, joint_type, row.q_min, row.q_max)
            else:
                numeric = float(value)
                values = [row.a, row.alpha, row.d, row.theta_offset, row.joint_type, row.q_min, row.q_max]
                values[col] = numeric
                new_row = DHRow(
                    a=float(values[0]),
                    alpha=float(values[1]),
                    d=float(values[2]),
                    theta_offset=float(values[3]),
                    joint_type=values[4],
                    q_min=float(values[5]),
                    q_max=float(values[6]),
                )
        except (TypeError, ValueError):
            return False
        self.rows[index.row()] = new_row
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def headerData(self, section, orientation, role=None):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None
