from __future__ import annotations

try:
    from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
except Exception:  # pragma: no cover
    class QAbstractListModel:  # type: ignore
        def __init__(self, *args, **kwargs): ...
    class QModelIndex:  # type: ignore
        pass
    class Qt:  # type: ignore
        DisplayRole = 0
        UserRole = 256


class RobotLibraryModel(QAbstractListModel):  # pragma: no cover - GUI shell
    NAME_ROLE = getattr(Qt, 'UserRole', 256) + 1
    LABEL_ROLE = getattr(Qt, 'UserRole', 256) + 2
    DOF_ROLE = getattr(Qt, 'UserRole', 256) + 3
    DESCRIPTION_ROLE = getattr(Qt, 'UserRole', 256) + 4
    METADATA_ROLE = getattr(Qt, 'UserRole', 256) + 5

    def __init__(self, entries=None, parent=None):
        super().__init__(parent)
        self._entries = list(entries or [])

    def rowCount(self, parent=QModelIndex()):  # type: ignore[override]
        return 0 if parent and getattr(parent, 'isValid', lambda: False)() else len(self._entries)

    def data(self, index, role=getattr(Qt, 'DisplayRole', 0)):  # type: ignore[override]
        if not getattr(index, 'isValid', lambda: False)():
            return None
        entry = self._entries[index.row()]
        if role == getattr(Qt, 'DisplayRole', 0):
            label = getattr(entry, 'label', getattr(entry, 'name', ''))
            dof = getattr(entry, 'dof', None)
            return f'{label} ({int(dof)} DOF)' if dof is not None else str(label)
        if role == self.NAME_ROLE:
            return str(getattr(entry, 'name', ''))
        if role == self.LABEL_ROLE:
            return str(getattr(entry, 'label', getattr(entry, 'name', '')))
        if role == self.DOF_ROLE:
            dof = getattr(entry, 'dof', None)
            return None if dof is None else int(dof)
        if role == self.DESCRIPTION_ROLE:
            return str(getattr(entry, 'description', ''))
        if role == self.METADATA_ROLE:
            return dict(getattr(entry, 'metadata', {}) or {})
        return None

    def roleNames(self):  # type: ignore[override]
        return {
            self.NAME_ROLE: b'name',
            self.LABEL_ROLE: b'label',
            self.DOF_ROLE: b'dof',
            self.DESCRIPTION_ROLE: b'description',
            self.METADATA_ROLE: b'metadata',
        }

    def set_entries(self, entries) -> None:
        if hasattr(self, 'beginResetModel'):
            self.beginResetModel()
        self._entries = list(entries or [])
        if hasattr(self, 'endResetModel'):
            self.endResetModel()
