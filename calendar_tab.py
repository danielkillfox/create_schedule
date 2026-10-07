# calendar_tab.py
"""Вкладка 7: сетка пар 6x5 (слева 1-6, сверху Пн-Пт).

Данные берутся из вкладки 6 (таблица schedule) и фильтруются
по преподавателю — так же, как на вкладке 6.
День недели хранится в schedule.weekday (0=Пн..4=Пт),
пара — в schedule.pair_number (1..6).
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт"]
PAIRS = [1, 2, 3, 4, 5, 6]

KIND_SHORT = {"lecture": "Л", "practice": "П"}

CELL_NORMAL = """
    QFrame { background-color: #363636; border: 1px solid #4a4a4a;
             border-radius: 4px; }
    QFrame:hover { border: 1px solid #66bb6a; }
"""
CELL_FILLED = """
    QFrame { background-color: #3a3f3a; border: 1px solid #5a6a5a;
             border-radius: 4px; }
    QFrame:hover { border: 1px solid #66bb6a; }
"""


class SlotCell(QFrame):
    """Одна ячейка сетки (пара x день недели), только для показа."""

    clicked = pyqtSignal(int, int)  # pair, day_col (0-4)

    def __init__(self, pair: int, day_col: int, parent=None):
        super().__init__(parent)
        self.pair = pair
        self.day_col = day_col
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(CELL_NORMAL)
        self.setMinimumHeight(84)
        self.setMinimumWidth(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        self.text_label = QLabel("")
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(
            "background: transparent; color: #e6e6e6; font-size: 12px;"
        )
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.text_label)
        layout.addStretch(1)

    def set_text(self, text: str):
        self.text_label.setText(text)
        self.setStyleSheet(CELL_FILLED if text else CELL_NORMAL)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.pair, self.day_col)
        super().mousePressEvent(event)


class CalendarTab(QWidget):
    """Вкладка-сетка: строки 1-6, столбцы Пн-Пт, фильтр по преподавателю."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.cells: dict[tuple[int, int], SlotCell] = {}
        self._details: dict[tuple[int, int], str] = {}
        self._build_ui()
        self.reload_teachers()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.addWidget(QLabel("Преподаватель:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.currentIndexChanged.connect(self.render)
        top.addWidget(self.teacher_combo, 1)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.render)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        grid = QGridLayout()
        grid.setSpacing(2)

        grid.addWidget(QLabel(""), 0, 0)

        for col, name in enumerate(WEEKDAYS):
            lbl = QLabel(name, alignment=Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-weight: bold;")
            grid.addWidget(lbl, 0, col + 1)

        for row, pair in enumerate(PAIRS):
            num = QLabel(str(pair), alignment=Qt.AlignmentFlag.AlignCenter)
            num.setStyleSheet("font-weight: bold;")
            num.setFixedWidth(36)
            grid.addWidget(num, row + 1, 0)
            for col in range(len(WEEKDAYS)):
                cell = SlotCell(pair, col)
                cell.clicked.connect(self.show_details)
                grid.addWidget(cell, row + 1, col + 1)
                self.cells[(pair, col)] = cell

        grid.setColumnStretch(0, 0)
        for col in range(len(WEEKDAYS)):
            grid.setColumnStretch(col + 1, 1)
        for row in range(len(PAIRS)):
            grid.setRowStretch(row + 1, 1)

        layout.addLayout(grid, 1)

    # ---- преподаватели (как на вкладке 6) ----

    def reload_teachers(self, keep_id: int | None = None):
        """Перечитать список преподавателей, по возможности сохранив выбор."""
        if keep_id is None:
            cur = self.teacher_combo.currentData()
        else:
            cur = keep_id
        self.teacher_combo.blockSignals(True)
        try:
            self.teacher_combo.clear()
            for t in self.db.get_teachers():
                self.teacher_combo.addItem(str(t["name"]), int(t["id"]))
            if cur is not None:
                idx = self.teacher_combo.findData(int(cur))
                if idx >= 0:
                    self.teacher_combo.setCurrentIndex(idx)
        finally:
            self.teacher_combo.blockSignals(False)
        self.render()

    def set_teacher(self, teacher_id: int | None):
        """Выбрать преподавателя (используется кнопкой с вкладки 6)."""
        if teacher_id is None:
            return
        idx = self.teacher_combo.findData(int(teacher_id))
        if idx >= 0:
            self.teacher_combo.setCurrentIndex(idx)
        else:
            self.reload_teachers(keep_id=int(teacher_id))
        self.render()

    def current_teacher_id(self) -> int | None:
        return self.teacher_combo.currentData()

    # ---- отрисовка из schedule ----

    def render(self):
        for cell in self.cells.values():
            cell.set_text("")
        self._details = {}

        tid = self.teacher_combo.currentData()
        if tid is None:
            return

        try:
            rows = self.db.get_teacher_schedule(int(tid))
        except Exception:
            return

        # Группируем по (weekday, pair)
        grouped: dict[tuple[int, int], list[dict]] = {}
        for r in rows:
            try:
                w = int(r.get("weekday", 0) or 0)
            except (TypeError, ValueError):
                w = 0
            try:
                p = int(r.get("pair_number", 1) or 1)
            except (TypeError, ValueError):
                p = 1
            if not (0 <= w <= 4 and 1 <= p <= 6):
                continue
            grouped.setdefault((w, p), []).append(dict(r))

        for (w, p), items in grouped.items():
            cell = self.cells.get((p, w))
            if cell is None:
                continue
            # Короткий текст в ячейку + полный в попап
            short_lines: list[str] = []
            full_lines: list[str] = []
            # Группируем внутри ячейки по (предмет, аудитория)
            inner: dict[tuple[str, str, str], list[dict]] = {}
            for it in items:
                key = (
                    str(it.get("subject_name") or "—"),
                    str(it.get("aud_name") or "—"),
                    str(it.get("kind") or ""),
                )
                inner.setdefault(key, []).append(it)
            for (subj, aud, kind), lst in sorted(inner.items()):
                groups = ", ".join(sorted({str(x.get("group_name", "")) for x in lst}))
                k = KIND_SHORT.get(kind, "")
                tag = f" [{k}]" if k else ""
                short_lines.append(f"{subj}{tag}\n{groups}\n{aud}")
                full_lines.append(
                    f"{subj}{tag} — {groups} — {aud} "
                    f"(пара {p}, {WEEKDAYS[w]})"
                )
            cell.set_text("\n— — —\n".join(short_lines))
            self._details[(p, w)] = "\n".join(full_lines)

    def show_details(self, pair: int, day_col: int):
        text = self._details.get((pair, day_col), "")
        if not text:
            return
        QMessageBox.information(
            self, f"Пара {pair}, {WEEKDAYS[day_col]}", text
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.render()
