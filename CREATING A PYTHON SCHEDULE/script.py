# main.py
import sys
from PyQt6.QtWidgets import (
    QApplication, QAbstractItemView, QFormLayout, QHBoxLayout,
    QHeaderView, QMessageBox, QPushButton, QSpinBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
    QProgressBar, QFrame, QLabel, QTabWidget, QComboBox, QGroupBox,
)
from PyQt6.QtCore import Qt

from db import DB


# это ооооочень важно не трогать блин
DARK_STYLE = """
QWidget {
    background-color: #2b2b2b;
    color: #e6e6e6;
    font-size: 13px;
}
QLabel { background: transparent; }
QPushButton {
    background-color: #3d3d3d;
    color: #e6e6e6;
    border: 1px solid #5a5a5a;
    border-radius: 4px;
    padding: 8px 16px;
}
QPushButton:hover { background-color: #4c4c4c; }
QPushButton:pressed { background-color: #5e5e5e; }
QSpinBox, QTableWidget, QTextEdit, QComboBox, QLineEdit {
    background-color: #1e1e1e;
    color: #e6e6e6;
    border: 1px solid #5a5a5a;
    padding: 4px;
}
QTableWidget { gridline-color: #4a4a4a; }
QTableWidget::item:selected { background-color: #3a5a8a; }
QHeaderView::section {
    background-color: #3d3d3d;
    color: #e6e6e6;
    border: 1px solid #5a5a5a;
}
QTextEdit { font-family: Consolas, monospace; }
QProgressBar { border: none; text-align: center; background: #333; color: white; }
QProgressBar::chunk { background: #4caf50; }
QTabWidget::pane { border: 1px solid #5a5a5a; }
QTabBar::tab {
    background: #3d3d3d; color: #e6e6e6; padding: 6px 12px;
    border: 1px solid #5a5a5a; border-bottom: none;
}
QTabBar::tab:selected { background: #4c4c4c; }
QGroupBox {
    border: 1px solid #5a5a5a;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QComboBox QAbstractItemView {
    background: #1e1e1e;
    selection-background-color: #3a5a8a;
}
"""


def create_cells(count, places):
    return [
        {"number": n, "places": places, "groups": [], "people": 0}
        for n in range(1, count + 1)
    ]


def place_optimal(groups, cells):
    n = len(groups)
    caps = [c["places"] for c in cells]
    order = sorted(range(n), key=lambda i: groups[i]["people_count"], reverse=True)
    loads = [0] * len(caps)
    assign = [None] * n
    best = {"count": -1, "people": -1, "assign": None}

    def backtrack(k, placed_count, placed_people):
        if (placed_count > best["count"]
                or (placed_count == best["count"] and placed_people > best["people"])):
            best["count"] = placed_count
            best["people"] = placed_people
            best["assign"] = assign[:]

        if k == n:
            return

        idx = order[k]
        size = groups[idx]["people_count"]

        tried = set()
        for c in range(len(caps)):
            if loads[c] + size <= caps[c] and loads[c] not in tried:
                tried.add(loads[c])
                loads[c] += size
                assign[idx] = c
                backtrack(k + 1, placed_count + 1, placed_people + size)
                loads[c] -= size
                assign[idx] = None

        backtrack(k + 1, placed_count, placed_people)

    backtrack(0, 0, 0)

    not_placed = []
    for i, g in enumerate(groups):
        c = best["assign"][i]
        if c is None:
            not_placed.append(g)
        else:
            cells[c]["groups"].append(g)
            cells[c]["people"] += g["people_count"]
    return not_placed


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Распределение групп по аудиториям")
        self.resize(1050, 850)

        self.db = DB("schedule.db")

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_groups = QWidget()
        self.tab_auds = QWidget()
        self.tab_teachers = QWidget()
        self.tab_subjects = QWidget()
        self.tab_distribute = QWidget()

        self.tabs.addTab(self.tab_groups, "1. Группы")
        self.tabs.addTab(self.tab_auds, "2. Аудитории")
        self.tabs.addTab(self.tab_teachers, "3. Преподаватели")
        self.tabs.addTab(self.tab_subjects, "4. Предметы")
        self.tabs.addTab(self.tab_distribute, "5. Распределение")

        self._build_groups_tab()
        self._build_auds_tab()
        self._build_teachers_tab()
        self._build_subjects_tab()
        self._build_distribute_tab()

        self.setLayout(layout)

        # Первичная загрузка
        self.reload_groups()
        self.reload_auditoriums()
        self.reload_teachers()
        self.reload_subjects()
        self.reload_courses()

    # ============================================================
    # 1. ВКЛАДКА "ГРУППЫ"
    # ============================================================
    def _build_groups_tab(self):
        v = QVBoxLayout()
        self.tab_groups.setLayout(v)

        # --- Поля ввода ---
        box = QGroupBox("Добавить группу")
        form = QHBoxLayout()
        form.addWidget(QLabel("Название:"))
        self.g_name = QLineEdit()
        self.g_name.setPlaceholderText("например, ИС-21")
        form.addWidget(self.g_name, 3)

        form.addWidget(QLabel("Студентов:"))
        self.g_students = QSpinBox(minimum=1, maximum=10000, value=20)
        form.addWidget(self.g_students)

        form.addWidget(QLabel("Курс:"))
        self.g_course = QSpinBox(minimum=1, maximum=6, value=1)
        form.addWidget(self.g_course)

        btn = QPushButton("Добавить")
        btn.clicked.connect(self.add_group)
        form.addWidget(btn)

        box.setLayout(form)
        v.addWidget(box)

        # --- Таблица ---
        v.addWidget(QLabel("Список групп:"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Группа", "Кол-во людей", "Курс"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 80)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        v.addWidget(self.table)

        btns = QHBoxLayout()
        del_btn = QPushButton("Удалить выбранную")
        del_btn.clicked.connect(self.delete_selected_group)
        reload_btn = QPushButton("Обновить из БД")
        reload_btn.clicked.connect(self.reload_groups)
        clear_btn = QPushButton("Очистить все группы")
        clear_btn.clicked.connect(self.clear_groups)
        btns.addWidget(del_btn)
        btns.addStretch()
        btns.addWidget(reload_btn)
        btns.addWidget(clear_btn)
        v.addLayout(btns)

    def reload_groups(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        try:
            for g in self.db.get_groups():
                r = self.table.rowCount()
                self.table.insertRow(r)
                item = QTableWidgetItem(str(g["name"]))
                item.setData(Qt.ItemDataRole.UserRole, int(g["id"]))
                self.table.setItem(r, 0, item)
                self.table.setItem(r, 1, QTableWidgetItem(str(g["students"])))
                self.table.setItem(r, 2, QTableWidgetItem(str(g["course"])))
            self.table.clearSelection()
        finally:
            self.table.blockSignals(False)

    def add_group(self):
        name = self.g_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название группы.")
            return
        try:
            self.db.add_group(name, self.g_students.value(), self.g_course.value())
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.g_name.clear()
        self.reload_groups()
        self.reload_courses()

    def delete_selected_group(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        gid = item.data(Qt.ItemDataRole.UserRole)
        if gid is None:
            return
        name = item.text()
        if QMessageBox.question(self, "Удаление", f"Удалить группу «{name}»?") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_group(int(gid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.reload_groups()
        self.reload_courses()

    def clear_groups(self):
        if QMessageBox.question(self, "Очистка", "Удалить ВСЕ группы?") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.clear_groups()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
        self.reload_groups()
        self.reload_courses()

    # ============================================================
    # 2. ВКЛАДКА "АУДИТОРИИ"
    # ============================================================
    def _build_auds_tab(self):
        v = QVBoxLayout()
        self.tab_auds.setLayout(v)

        box = QGroupBox("Добавить аудиторию")
        form = QHBoxLayout()
        form.addWidget(QLabel("Название:"))
        self.a_name = QLineEdit()
        self.a_name.setPlaceholderText("например, А-101")
        form.addWidget(self.a_name, 3)

        form.addWidget(QLabel("Вместимость:"))
        self.a_capacity = QSpinBox(minimum=1, maximum=10000, value=25)
        form.addWidget(self.a_capacity)

        btn = QPushButton("Добавить")
        btn.clicked.connect(self.add_auditorium)
        form.addWidget(btn)
        box.setLayout(form)
        v.addWidget(box)

        v.addWidget(QLabel("Список аудиторий:"))
        self.aud_table = QTableWidget(0, 2)
        self.aud_table.setHorizontalHeaderLabels(["Аудитория", "Вместимость"])
        self.aud_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.aud_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.aud_table.setColumnWidth(1, 120)
        self.aud_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.aud_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        v.addWidget(self.aud_table)

        btns = QHBoxLayout()
        del_btn = QPushButton("Удалить выбранную")
        del_btn.clicked.connect(self.delete_selected_aud)
        reload_btn = QPushButton("Обновить из БД")
        reload_btn.clicked.connect(self.reload_auditoriums)
        clear_btn = QPushButton("Очистить все аудитории")
        clear_btn.clicked.connect(self.clear_auditoriums)
        btns.addWidget(del_btn)
        btns.addStretch()
        btns.addWidget(reload_btn)
        btns.addWidget(clear_btn)
        v.addLayout(btns)

    def reload_auditoriums(self):
        self.aud_table.blockSignals(True)
        self.aud_table.setRowCount(0)
        try:
            for a in self.db.get_auditoriums():
                r = self.aud_table.rowCount()
                self.aud_table.insertRow(r)
                item = QTableWidgetItem(str(a["name"]))
                item.setData(Qt.ItemDataRole.UserRole, int(a["id"]))
                self.aud_table.setItem(r, 0, item)
                self.aud_table.setItem(r, 1, QTableWidgetItem(str(a["capacity"])))
            self.aud_table.clearSelection()
        finally:
            self.aud_table.blockSignals(False)

    def add_auditorium(self):
        name = self.a_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название аудитории.")
            return
        try:
            self.db.add_auditorium(name, self.a_capacity.value())
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.a_name.clear()
        self.reload_auditoriums()

    def delete_selected_aud(self):
        row = self.aud_table.currentRow()
        if row < 0:
            return
        item = self.aud_table.item(row, 0)
        if item is None:
            return
        aid = item.data(Qt.ItemDataRole.UserRole)
        if aid is None:
            return
        name = item.text()
        if QMessageBox.question(self, "Удаление", f"Удалить аудиторию «{name}»?") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_auditorium(int(aid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.reload_auditoriums()

    def clear_auditoriums(self):
        if QMessageBox.question(self, "Очистка", "Удалить ВСЕ аудитории?") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.clear_auditoriums()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
        self.reload_auditoriums()

    # ============================================================
    # 3. ВКЛАДКА "ПРЕПОДАВАТЕЛИ"
    # ============================================================
    def _build_teachers_tab(self):
        v = QVBoxLayout()
        self.tab_teachers.setLayout(v)

        box = QGroupBox("Добавить преподавателя")
        form = QHBoxLayout()
        form.addWidget(QLabel("Имя:"))
        self.t_name = QLineEdit()
        self.t_name.setPlaceholderText("например, Иванов И.И.")
        form.addWidget(self.t_name, 1)
        btn = QPushButton("Добавить")
        btn.clicked.connect(self.add_teacher)
        form.addWidget(btn)
        box.setLayout(form)
        v.addWidget(box)

        h = QHBoxLayout()

        # Левая колонка
        left = QVBoxLayout()
        left.addWidget(QLabel("Преподаватели:"))
        self.teachers_table = QTableWidget(0, 1)
        self.teachers_table.setHorizontalHeaderLabels(["Имя"])
        self.teachers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.teachers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.teachers_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.teachers_table.itemSelectionChanged.connect(self.on_teacher_selected)
        left.addWidget(self.teachers_table)

        del_t = QPushButton("Удалить преподавателя")
        del_t.clicked.connect(self.delete_selected_teacher)
        left.addWidget(del_t)

        # Правая колонка
        right = QVBoxLayout()
        right.addWidget(QLabel("Предметы этого преподавателя:"))
        self.teacher_subjects_table = QTableWidget(0, 1)
        self.teacher_subjects_table.setHorizontalHeaderLabels(["Предмет"])
        self.teacher_subjects_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.teacher_subjects_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        right.addWidget(self.teacher_subjects_table)

        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("Привязать:"))
        self.subj_for_teacher_combo = QComboBox()
        add_row.addWidget(self.subj_for_teacher_combo, 1)
        add_btn = QPushButton("Привязать")
        add_btn.clicked.connect(self.assign_subject_to_teacher)
        add_row.addWidget(add_btn)
        right.addLayout(add_row)

        unassign_btn = QPushButton("Отвязать выбранный предмет")
        unassign_btn.clicked.connect(self.unassign_subject_from_teacher)
        right.addWidget(unassign_btn)

        h.addLayout(left, 1)
        h.addLayout(right, 1)
        v.addLayout(h)

    def reload_teachers(self):
        self.teachers_table.blockSignals(True)
        self.teachers_table.setRowCount(0)
        try:
            for t in self.db.get_teachers():
                r = self.teachers_table.rowCount()
                self.teachers_table.insertRow(r)
                item = QTableWidgetItem(str(t["name"]))
                item.setData(Qt.ItemDataRole.UserRole, int(t["id"]))
                self.teachers_table.setItem(r, 0, item)
            self.teachers_table.clearSelection()
        finally:
            self.teachers_table.blockSignals(False)
        self.teacher_subjects_table.setRowCount(0)
        self._reload_subj_for_teacher_combo()

    def _reload_subj_for_teacher_combo(self):
        self.subj_for_teacher_combo.clear()
        for s in self.db.get_subjects():
            self.subj_for_teacher_combo.addItem(str(s["name"]), int(s["id"]))

    def on_teacher_selected(self):
        self.teacher_subjects_table.blockSignals(True)
        self.teacher_subjects_table.setRowCount(0)
        try:
            row = self.teachers_table.currentRow()
            if row < 0:
                return
            item = self.teachers_table.item(row, 0)
            if item is None:
                return
            tid = item.data(Qt.ItemDataRole.UserRole)
            if tid is None:
                return
            for s in self.db.get_subjects_of_teacher(int(tid)):
                r = self.teacher_subjects_table.rowCount()
                self.teacher_subjects_table.insertRow(r)
                it = QTableWidgetItem(str(s["name"]))
                it.setData(Qt.ItemDataRole.UserRole, int(s["id"]))
                self.teacher_subjects_table.setItem(r, 0, it)
        finally:
            self.teacher_subjects_table.blockSignals(False)

    def add_teacher(self):
        name = self.t_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя.")
            return
        try:
            self.db.add_teacher(name)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.t_name.clear()
        self.reload_teachers()

    def delete_selected_teacher(self):
        row = self.teachers_table.currentRow()
        if row < 0:
            return
        item = self.teachers_table.item(row, 0)
        if item is None:
            return
        tid = item.data(Qt.ItemDataRole.UserRole)
        if tid is None:
            return
        name = item.text()
        if QMessageBox.question(self, "Удаление", f"Удалить преподавателя «{name}»?") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_teacher(int(tid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.reload_teachers()

    def assign_subject_to_teacher(self):
        row = self.teachers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите преподавателя слева.")
            return
        item = self.teachers_table.item(row, 0)
        if item is None:
            return
        tid = item.data(Qt.ItemDataRole.UserRole)
        if tid is None:
            return
        sid = self.subj_for_teacher_combo.currentData()
        if sid is None:
            QMessageBox.warning(self, "Ошибка", "Нет доступных предметов.")
            return
        try:
            self.db.assign_teacher_subject(int(tid), int(sid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.on_teacher_selected()

    def unassign_subject_from_teacher(self):
        row = self.teachers_table.currentRow()
        if row < 0:
            return
        titem = self.teachers_table.item(row, 0)
        if titem is None:
            return
        tid = titem.data(Qt.ItemDataRole.UserRole)
        if tid is None:
            return
        srow = self.teacher_subjects_table.currentRow()
        if srow < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите предмет справа.")
            return
        sitem = self.teacher_subjects_table.item(srow, 0)
        if sitem is None:
            return
        sid = sitem.data(Qt.ItemDataRole.UserRole)
        if sid is None:
            return
        try:
            self.db.unassign_teacher_subject(int(tid), int(sid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.on_teacher_selected()

    # ============================================================
    # 4. ВКЛАДКА "ПРЕДМЕТЫ"
    # ============================================================
    def _build_subjects_tab(self):
        v = QVBoxLayout()
        self.tab_subjects.setLayout(v)

        box = QGroupBox("Добавить предмет")
        form = QHBoxLayout()
        form.addWidget(QLabel("Название:"))
        self.s_name = QLineEdit()
        self.s_name.setPlaceholderText("например, Математика")
        form.addWidget(self.s_name, 1)
        btn = QPushButton("Добавить")
        btn.clicked.connect(self.add_subject)
        form.addWidget(btn)
        box.setLayout(form)
        v.addWidget(box)

        h = QHBoxLayout()

        # Левая колонка — предметы
        left = QVBoxLayout()
        left.addWidget(QLabel("Предметы:"))
        self.subjects_table = QTableWidget(0, 1)
        self.subjects_table.setHorizontalHeaderLabels(["Название"])
        self.subjects_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.subjects_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.subjects_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.subjects_table.itemSelectionChanged.connect(self.on_subject_selected)
        left.addWidget(self.subjects_table)

        del_s = QPushButton("Удалить предмет")
        del_s.clicked.connect(self.delete_selected_subject)
        left.addWidget(del_s)

        # Правая колонка — курсы предмета
        right = QVBoxLayout()
        right.addWidget(QLabel("Курсы, где читается предмет:"))
        self.subject_courses_table = QTableWidget(0, 1)
        self.subject_courses_table.setHorizontalHeaderLabels(["Курс"])
        self.subject_courses_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.subject_courses_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        right.addWidget(self.subject_courses_table)

        # Выбор курса через ComboBox
        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("Добавить курс:"))
        self.course_for_subject_combo = QComboBox()
        for n in range(1, 7):
            self.course_for_subject_combo.addItem(f"{n} курс", n)
        add_row.addWidget(self.course_for_subject_combo, 1)
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_course_to_subject)
        add_row.addWidget(add_btn)
        right.addLayout(add_row)

        del_btn = QPushButton("Убрать выбранный курс")
        del_btn.clicked.connect(self.remove_course_from_subject)
        right.addWidget(del_btn)

        h.addLayout(left, 1)
        h.addLayout(right, 1)
        v.addLayout(h)

    def reload_subjects(self):
        self.subjects_table.blockSignals(True)
        self.subjects_table.setRowCount(0)
        try:
            for s in self.db.get_subjects():
                r = self.subjects_table.rowCount()
                self.subjects_table.insertRow(r)
                item = QTableWidgetItem(str(s["name"]))
                item.setData(Qt.ItemDataRole.UserRole, int(s["id"]))
                self.subjects_table.setItem(r, 0, item)
            self.subjects_table.clearSelection()
        finally:
            self.subjects_table.blockSignals(False)
        self.subject_courses_table.setRowCount(0)
        self._reload_subj_for_teacher_combo()

    def on_subject_selected(self):
        self.subject_courses_table.blockSignals(True)
        self.subject_courses_table.setRowCount(0)
        try:
            row = self.subjects_table.currentRow()
            if row < 0:
                return
            item = self.subjects_table.item(row, 0)
            if item is None:
                return
            sid = item.data(Qt.ItemDataRole.UserRole)
            if sid is None:
                return
            for cnum in self.db.get_courses_of_subject(int(sid)):
                r = self.subject_courses_table.rowCount()
                self.subject_courses_table.insertRow(r)
                self.subject_courses_table.setItem(r, 0, QTableWidgetItem(str(cnum)))
        finally:
            self.subject_courses_table.blockSignals(False)

    def add_subject(self):
        name = self.s_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название предмета.")
            return
        try:
            self.db.add_subject(name)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.s_name.clear()
        self.reload_subjects()

    def delete_selected_subject(self):
        row = self.subjects_table.currentRow()
        if row < 0:
            return
        item = self.subjects_table.item(row, 0)
        if item is None:
            return
        sid = item.data(Qt.ItemDataRole.UserRole)
        if sid is None:
            return
        name = item.text()
        if QMessageBox.question(self, "Удаление", f"Удалить предмет «{name}»?") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_subject(int(sid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.reload_subjects()
        self.reload_courses()

    def add_course_to_subject(self):
        row = self.subjects_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите предмет слева.")
            return
        item = self.subjects_table.item(row, 0)
        if item is None:
            return
        sid = item.data(Qt.ItemDataRole.UserRole)
        if sid is None:
            return
        cnum = self.course_for_subject_combo.currentData()
        if cnum is None:
            return
        try:
            self.db.add_course_subject(int(cnum), int(sid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.on_subject_selected()
        self.reload_courses()

    def remove_course_from_subject(self):
        row = self.subjects_table.currentRow()
        if row < 0:
            return
        sitem = self.subjects_table.item(row, 0)
        if sitem is None:
            return
        sid = sitem.data(Qt.ItemDataRole.UserRole)
        if sid is None:
            return
        crow = self.subject_courses_table.currentRow()
        if crow < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите курс справа.")
            return
        citem = self.subject_courses_table.item(crow, 0)
        if citem is None:
            return
        try:
            cnum = int(citem.text())
            self.db.remove_course_subject(cnum, int(sid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.on_subject_selected()
        self.reload_courses()

    # ============================================================
    # 5. ВКЛАДКА "РАСПРЕДЕЛЕНИЕ"
    # ============================================================
    def _build_distribute_tab(self):
        v = QVBoxLayout()
        self.tab_distribute.setLayout(v)

        # --- Шаг 1 и 2 ---
        sel_box = QGroupBox("Выберите, что распределять")
        form = QFormLayout()

        self.course_combo = QComboBox()
        self.subject_combo = QComboBox()
        form.addRow(QLabel("Шаг 1. Курс:"), self.course_combo)
        form.addRow(QLabel("Шаг 2. Предмет:"), self.subject_combo)
        sel_box.setLayout(form)
        v.addWidget(sel_box)

        self.course_combo.currentIndexChanged.connect(self.on_course_changed)
        self.subject_combo.currentIndexChanged.connect(self.on_subject_changed)

        # --- Превью групп ---
        gbox = QGroupBox("Группы этого курса (они будут распределены)")
        gv = QVBoxLayout()
        self.groups_preview = QTableWidget(0, 2)
        self.groups_preview.setHorizontalHeaderLabels(["Группа", "Человек"])
        self.groups_preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.groups_preview.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.groups_preview.setColumnWidth(1, 100)
        self.groups_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.groups_preview.setMaximumHeight(180)
        gv.addWidget(self.groups_preview)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #9aa;")
        gv.addWidget(self.summary_label)
        gbox.setLayout(gv)
        v.addWidget(gbox)

        # --- Кнопка запуска ---
        run_btn = QPushButton("▶ Распределить по аудиториям")
        run_btn.setStyleSheet(
            "QPushButton { font-weight: bold; background-color: #2e7d32; "
            "padding: 10px 16px; font-size: 14px; }"
            "QPushButton:hover { background-color: #388e3c; }"
        )
        run_btn.clicked.connect(self.distribute)
        v.addWidget(run_btn)

        # --- Результаты ---
        rbox = QGroupBox("Результат")
        rv = QVBoxLayout()

        self.toggle_btn = QPushButton("Показать таблицу")
        self.toggle_btn.clicked.connect(self.toggle_result_mode)
        rv.addWidget(self.toggle_btn)

        self.result_container = QFrame()
        res_layout = QVBoxLayout()
        res_layout.setContentsMargins(4, 4, 4, 4)
        self.result_container.setLayout(res_layout)

        self.text_result = QTextEdit()
        self.text_result.setReadOnly(True)
        self.text_result.setMinimumHeight(260)
        res_layout.addWidget(self.text_result)

        self.table_result = QTableWidget()
        self.table_result.setVisible(False)
        self.table_result.setColumnCount(6)
        self.table_result.setHorizontalHeaderLabels(
            ["Ячейка", "Занято", "Свободно", "%", "Состав", "Прогресс"]
        )
        header = self.table_result.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table_result.setColumnWidth(5, 90)
        res_layout.addWidget(self.table_result)

        rv.addWidget(self.result_container)
        rbox.setLayout(rv)
        v.addWidget(rbox)

    def reload_courses(self):
        self.course_combo.blockSignals(True)
        self.course_combo.clear()
        try:
            courses = sorted({g["course"] for g in self.db.get_groups()})
            for n in courses:
                self.course_combo.addItem(f"{n} курс", int(n))
        finally:
            self.course_combo.blockSignals(False)
        self.on_course_changed()

    def on_course_changed(self):
        course = self.course_combo.currentData()
        if course is None:
            self.subject_combo.blockSignals(True)
            self.subject_combo.clear()
            self.subject_combo.blockSignals(False)
            self.groups_preview.setRowCount(0)
            self.summary_label.setText("")
            self.text_result.clear()
            self.table_result.setRowCount(0)
            return

        self.subject_combo.blockSignals(True)
        self.subject_combo.clear()
        try:
            for s in self.db.get_course_subjects(int(course)):
                self.subject_combo.addItem(str(s["name"]), int(s["id"]))
        finally:
            self.subject_combo.blockSignals(False)

        self.groups_preview.blockSignals(True)
        self.groups_preview.setRowCount(0)
        try:
            groups = self.db.get_groups_by_course(int(course))
            for g in groups:
                r = self.groups_preview.rowCount()
                self.groups_preview.insertRow(r)
                self.groups_preview.setItem(r, 0, QTableWidgetItem(str(g["name"])))
                self.groups_preview.setItem(r, 1, QTableWidgetItem(str(g["students"])))
        finally:
            self.groups_preview.blockSignals(False)

        auds = self.db.get_auditoriums()
        self.summary_label.setText(
            f"Групп: {self.groups_preview.rowCount()}  ·  "
            f"Аудиторий в базе: {len(auds)}"
        )

        self.on_subject_changed()

    def on_subject_changed(self):
        sid = self.subject_combo.currentData()
        if sid is None:
            self.text_result.setText(
                "Для этого курса ещё нет привязанных предметов.\n"
                "Перейдите на вкладку «4. Предметы» и привяжите предмет к курсу."
            )
            self.table_result.setRowCount(0)
            return
        saved = self.db.load_distribution(int(sid))
        if saved:
            lines = [f"Ранее сохранённое распределение для «{self.subject_combo.currentText()}»:"]
            for r in saved:
                lines.append(f"  {r['aud_name']}: {r['grp_name']} ({r['students']} чел.)")
            self.text_result.setText("\n".join(lines))
        else:
            self.text_result.setText(
                f"Для предмета «{self.subject_combo.currentText()}» распределения ещё нет.\n"
                f"Нажмите зелёную кнопку «Распределить по аудиториям»."
            )
        self.table_result.setRowCount(0)

    def toggle_result_mode(self):
        # иди нафиг
        show_text = self.table_result.isVisible()
        self.text_result.setVisible(show_text)
        self.table_result.setVisible(not show_text)
        self.toggle_btn.setText(
            "Показать таблицу" if show_text else "Показать текст"
        )

    def distribute(self):
        course = self.course_combo.currentData()
        subject_id = self.subject_combo.currentData()
        if course is None or subject_id is None:
            QMessageBox.warning(self, "Ошибка",
                                "Сначала выберите курс и предмет.")
            return

        db_groups = self.db.get_groups_by_course(int(course))
        db_auds = self.db.get_auditoriums()

        if not db_groups:
            QMessageBox.warning(self, "Ошибка", f"На {course} курсе нет групп.")
            return
        if not db_auds:
            QMessageBox.warning(self, "Ошибка", "В базе нет аудиторий.")
            return

        cells = [
            {"number": a["name"], "places": a["capacity"],
             "groups": [], "people": 0, "_id": a["id"]}
            for a in db_auds
        ]
        groups = [
            {"name": g["name"], "people_count": g["students"], "_id": g["id"]}
            for g in db_groups
        ]

        not_placed = place_optimal(groups, cells)

        assignments = [(g["_id"], cell["_id"]) for cell in cells for g in cell["groups"]]
        try:
            self.db.save_distribution(int(subject_id), assignments)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))

        total_p = sum(c["people"] for c in cells)
        total_pl = sum(c["places"] for c in cells)
        percent = (total_p / total_pl * 100) if total_pl > 0 else 0

        lines = [
            f"Курс {course}, предмет: {self.subject_combo.currentText()}",
            f"Общая заполненность: {percent:.1f}%",
            f"Всего людей: {total_p} из {total_pl}",
            f"Групп размещено: {sum(len(c['groups']) for c in cells)}",
            f"Не поместилось: {len(not_placed)}",
        ]
        for cell in cells:
            free = cell["places"] - cell["people"]
            names = ", ".join(
                f"{g['name']} ({g['people_count']} чел.)"
                for g in cell["groups"]
            ) or "пусто"
            lines.append("")
            lines.append(f"Аудитория {cell['number']}:")
            lines.append(f"Занято: {cell['people']} из {cell['places']} ({free} свободно)")
            lines.append(f"Состав: {names}")

        if not_placed:
            lines.append("")
            lines.append("!!! НЕ ПОМЕСТИЛИСЬ !!!")
            for g in not_placed:
                lines.append(f"- {g['name']} ({g['people_count']} чел.)")

        self.text_result.setText("\n".join(lines))

        self.table_result.setRowCount(0)
        for cell in cells:
            row = self.table_result.rowCount()
            self.table_result.insertRow(row)
            free = cell["places"] - cell["people"]
            p = cell["people"]
            places = cell["places"]
            pct = (p / places * 100) if places > 0 else 0
            names = ", ".join(
                f"{g['name']} ({g['people_count']} чел.)"
                for g in cell["groups"]
            ) or "пусто"

            self.table_result.setItem(row, 0, QTableWidgetItem(str(cell["number"])))
            self.table_result.setItem(row, 1, QTableWidgetItem(f"{p}"))
            self.table_result.setItem(row, 2, QTableWidgetItem(f"{free}"))
            self.table_result.setItem(row, 3, QTableWidgetItem(f"{pct:.1f}%"))
            self.table_result.setItem(row, 4, QTableWidgetItem(names))

            w = QWidget()
            bar = QProgressBar()
            bar.setRange(0, places)
            bar.setValue(p)
            bar.setTextVisible(False)
            l = QHBoxLayout()
            l.setContentsMargins(0, 0, 0, 0)
            l.addWidget(bar)
            w.setLayout(l)
            self.table_result.setCellWidget(row, 5, w)

        if not_placed:
            row = self.table_result.rowCount()
            self.table_result.insertRow(row)
            msg = "!!! НЕ ПОМЕСТИЛИСЬ: " + ", ".join(g["name"] for g in not_placed)
            item = QTableWidgetItem(msg)
            item.setForeground(Qt.GlobalColor.red)
            self.table_result.setItem(row, 0, item)
            self.table_result.setSpan(row, 0, 1, 6)

    # ============================================================
    # ЗАКРЫТИЕ
    # ============================================================
    def closeEvent(self, event):
        try:
            self.db.close()
        finally:
            super().closeEvent(event)


def run_gui():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()