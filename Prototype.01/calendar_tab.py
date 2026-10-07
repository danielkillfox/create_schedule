# calendar_tab.py
"""Вкладка «7. Календарь»: месячная сетка расписания.

Хранит занятия по календарным датам в таблице calendar_entries
(создаётся автоматически в schedule.db). Справочники групп, предметов
и преподавателей берутся из существующих таблиц прототипа.
"""

import calendar as calendar_mod
from datetime import date

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
NO_VALUE = "— не выбрано —"

SUBJECT_COLORS = [
    "#bbdefb", "#c8e6c9", "#fff9c4", "#f8bbd0",
    "#e1bee7", "#ffccbc", "#b2ebf2", "#ffe0b2",
]

CELL_EMPTY = """
    QFrame { background-color: #2b2b2b; border: 1px solid #383838;
             border-radius: 4px; color: #5a5a5a; }
"""
CELL_NORMAL = """
    QFrame { background-color: #363636; border: 1px solid #4a4a4a;
             border-radius: 4px; }
"""
CELL_TODAY = """
    QFrame { background-color: #3a5a3a; border: 2px solid #66bb6a;
             border-radius: 4px; }
"""


def _entry_color(subject_id):
    if not subject_id:
        return "#eceff1"
    return SUBJECT_COLORS[(int(subject_id) - 1) % len(SUBJECT_COLORS)]


class DayCell(QFrame):
    """Ячейка одного дня в месячной сетке."""

    clicked = pyqtSignal(object)  # datetime.date

    def __init__(self, parent=None):
        super().__init__(parent)
        self.day_date: date | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(84)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 4)
        layout.setSpacing(2)

        self.day_label = QLabel("")
        self.day_label.setStyleSheet(
            "font-weight: bold; background: transparent; color: #e6e6e6;"
        )
        layout.addWidget(self.day_label)

        self.entries_box = QVBoxLayout()
        self.entries_box.setSpacing(2)
        layout.addLayout(self.entries_box)
        layout.addStretch(1)

        self.set_day(None)

    def set_day(self, day_date: date | None, is_today: bool = False):
        self.day_date = day_date
        if day_date is None:
            self.setStyleSheet(CELL_EMPTY)
            self.day_label.setText("")
        elif is_today:
            self.setStyleSheet(CELL_TODAY)
            self.day_label.setText(str(day_date.day))
            self.day_label.setStyleSheet(
                "font-weight: bold; background: transparent; color: #c8e6c9;"
            )
        else:
            self.setStyleSheet(CELL_NORMAL)
            self.day_label.setText(str(day_date.day))
            self.day_label.setStyleSheet(
                "font-weight: bold; background: transparent; color: #e6e6e6;"
            )

    def clear_entries(self):
        while self.entries_box.count():
            item = self.entries_box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_entry(self, text: str, color: str):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(
            f"background: {color}; color: #17202a; border-radius: 3px; "
            f"padding: 1px 4px; font-size: 11px;"
        )
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.entries_box.addWidget(label)

    def mousePressEvent(self, event):
        if self.day_date is not None and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.day_date)
        super().mousePressEvent(event)


class DayDialog(QDialog):
    """Модальное окно: выбор групп, предмета и преподавателя на дату."""

    def __init__(self, db, day_date: date, parent=None):
        super().__init__(parent)
        self.db = db
        self.day_date = day_date

        self.setWindowTitle(f"Занятия на {day_date.strftime('%d.%m.%Y')}")
        self.setMinimumWidth(400)
        self.checkboxes: dict[int, QCheckBox] = {}

        self.groups = self.db.get_groups()
        self.subjects = self.db.get_subjects()
        self.teachers = self.db.get_teachers()
        entries = self._day_entries()
        assigned = {e["group_id"] for e in entries}

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Выберите группы:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(240)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(2)
        if not self.groups:
            inner_layout.addWidget(QLabel("Нет групп. Сначала добавьте их на вкладке «1. Группы»."))
        for g in self.groups:
            cb = QCheckBox(f"{g['name']} ({g['students']} чел.)")
            cb.setChecked(int(g["id"]) in assigned)
            self.checkboxes[int(g["id"])] = cb
            inner_layout.addWidget(cb)
        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        layout.addWidget(QLabel("Предмет:"))
        self.subject_combo = QComboBox()
        self.subject_combo.addItem(NO_VALUE, None)
        for s in self.subjects:
            self.subject_combo.addItem(str(s["name"]), int(s["id"]))
        initial_sid = entries[0].get("subject_id") if entries else None
        if initial_sid is not None:
            idx = self.subject_combo.findData(int(initial_sid))
            if idx >= 0:
                self.subject_combo.setCurrentIndex(idx)
        layout.addWidget(self.subject_combo)

        layout.addWidget(QLabel("Преподаватель:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.addItem(NO_VALUE, None)
        for t in self.teachers:
            self.teacher_combo.addItem(str(t["name"]), int(t["id"]))
        initial_tid = entries[0].get("teacher_id") if entries else None
        if initial_tid is not None:
            idx = self.teacher_combo.findData(int(initial_tid))
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)
        layout.addWidget(self.teacher_combo)

        if not self.subjects:
            lbl = QLabel("Нет предметов — добавьте их на вкладке «4. Предметы».")
            lbl.setStyleSheet("color: #e57373;")
            layout.addWidget(lbl)
        if not self.teachers:
            lbl = QLabel("Нет преподавателей — добавьте их на вкладке «3. Преподаватели».")
            lbl.setStyleSheet("color: #e57373;")
            layout.addWidget(lbl)

        buttons = QHBoxLayout()
        clear_btn = QPushButton("Очистить день")
        clear_btn.clicked.connect(self._clear_day)
        buttons.addWidget(clear_btn)
        buttons.addStretch(1)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        save_btn = QPushButton("Сохранить")
        save_btn.setStyleSheet(
            "QPushButton { font-weight: bold; background-color: #1565c0; }"
            "QPushButton:hover { background-color: #1976d2; }"
        )
        save_btn.clicked.connect(self._save)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        self.setModal(True)

    def _day_entries(self) -> list[dict]:
        cur = self.db.conn.execute(
            "SELECT group_id, subject_id, teacher_id FROM calendar_entries "
            "WHERE date = ? ORDER BY group_id",
            (self.day_date.isoformat(),),
        )
        return [dict(r) for r in cur.fetchall()]

    def _save(self):
        group_ids = [gid for gid, cb in self.checkboxes.items() if cb.isChecked()]
        subject_id = self.subject_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        iso = self.day_date.isoformat()
        try:
            with self.db.conn:
                self.db.conn.execute(
                    "DELETE FROM calendar_entries WHERE date = ?", (iso,)
                )
                self.db.conn.executemany(
                    "INSERT INTO calendar_entries "
                    "(date, group_id, subject_id, teacher_id) "
                    "VALUES (?, ?, ?, ?)",
                    [(iso, gid, subject_id, teacher_id) for gid in group_ids],
                )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.accept()

    def _clear_day(self):
        iso = self.day_date.isoformat()
        try:
            with self.db.conn:
                self.db.conn.execute(
                    "DELETE FROM calendar_entries WHERE date = ?", (iso,)
                )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)


class CalendarTab(QWidget):
    """Вкладка с месячной сеткой расписания."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        today = date.today()
        self.year = today.year
        self.month = today.month

        self._ensure_table()
        self._build_ui()
        self.render()

    def _ensure_table(self):
        with self.db.conn:
            self.db.conn.executescript("""
                CREATE TABLE IF NOT EXISTS calendar_entries (
                    id         INTEGER PRIMARY KEY,
                    date       TEXT    NOT NULL,
                    group_id   INTEGER NOT NULL,
                    subject_id INTEGER,
                    teacher_id INTEGER,
                    FOREIGN KEY (group_id)   REFERENCES groups(id)   ON DELETE CASCADE,
                    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cal_entries_date
                    ON calendar_entries(date);
            """)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QHBoxLayout()
        prev_btn = QPushButton("‹")
        prev_btn.setFixedWidth(36)
        prev_btn.clicked.connect(self.prev_month)
        header.addWidget(prev_btn)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.addWidget(self.title_label)

        next_btn = QPushButton("›")
        next_btn.setFixedWidth(36)
        next_btn.clicked.connect(self.next_month)
        header.addWidget(next_btn)

        today_btn = QPushButton("Сегодня")
        today_btn.clicked.connect(self.go_today)
        header.addWidget(today_btn)
        header.addStretch(1)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.render)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(2)
        for col, name in enumerate(WEEKDAYS):
            lbl = QLabel(name, alignment=Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-weight: bold;")
            grid.addWidget(lbl, 0, col)

        self.cells: dict[tuple[int, int], DayCell] = {}
        for row in range(6):
            for col in range(7):
                cell = DayCell()
                cell.clicked.connect(self.open_day)
                grid.addWidget(cell, row + 1, col)
                self.cells[(row, col)] = cell
        for col in range(7):
            grid.setColumnStretch(col, 1)
        for row in range(1, 7):
            grid.setRowStretch(row, 1)
        layout.addLayout(grid, 1)

    # ---- навигация ----

    def prev_month(self):
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1
        self.render()

    def next_month(self):
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
        self.render()

    def go_today(self):
        today = date.today()
        self.year, self.month = today.year, today.month
        self.render()

    # ---- отрисовка ----

    def _load_month_entries(self) -> dict[str, list[dict]]:
        start = date(self.year, self.month, 1)
        end = date(self.year, self.month, calendar_mod.monthrange(self.year, self.month)[1])
        cur = self.db.conn.execute(
            """
            SELECT e.date, e.group_id, e.subject_id, e.teacher_id,
                   g.name AS group_name,
                   COALESCE(s.name, '') AS subject_name,
                   COALESCE(t.name, '') AS teacher_name
            FROM calendar_entries e
            JOIN groups g ON g.id = e.group_id
            LEFT JOIN subjects s ON s.id = e.subject_id
            LEFT JOIN teachers t ON t.id = e.teacher_id
            WHERE e.date BETWEEN ? AND ?
            ORDER BY e.date, g.name
            """,
            (start.isoformat(), end.isoformat()),
        )
        by_date: dict[str, list[dict]] = {}
        for r in cur.fetchall():
            by_date.setdefault(r["date"], []).append(dict(r))
        return by_date

    def render(self):
        self.title_label.setText(f"{MONTHS[self.month - 1]} {self.year}")
        by_date = self._load_month_entries()

        cal = calendar_mod.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self.year, self.month)
        while len(weeks) < 6:
            weeks.append([])
        weeks = weeks[:6]

        today = date.today()
        for (row, col), cell in self.cells.items():
            cell.clear_entries()
            day = weeks[row][col] if row < len(weeks) and col < len(weeks[row]) else 0
            if day == 0:
                cell.set_day(None)
                continue
            day_date = date(self.year, self.month, day)
            cell.set_day(day_date, is_today=(day_date == today))
            for entry in by_date.get(day_date.isoformat(), []):
                parts = [entry["group_name"]]
                if entry["subject_name"]:
                    parts.append(entry["subject_name"])
                if entry["teacher_name"]:
                    parts.append(entry["teacher_name"])
                cell.add_entry(" · ".join(parts), _entry_color(entry["subject_id"]))

    def open_day(self, day_date: date):
        dialog = DayDialog(self.db, day_date, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.render()

    def showEvent(self, event):
        super().showEvent(event)
        self.render()
