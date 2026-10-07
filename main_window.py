
from contextlib import contextmanager

from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFileDialog, QFormLayout, QHBoxLayout,
    QHeaderView, QMessageBox, QPushButton, QSpinBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
    QProgressBar, QFrame, QLabel, QTabWidget, QComboBox, QGroupBox,
)
from PyQt6.QtCore import Qt

from db import DB, KIND_LECTURE, KIND_PRACTICE
from calendar_tab import CalendarTab, WEEKDAYS
import distributor


KIND_LABELS = {KIND_LECTURE: "Лекция", KIND_PRACTICE: "Практика"}


@contextmanager
def signals_blocked(widget):
    widget.blockSignals(True)
    try:
        yield widget
    finally:
        widget.blockSignals(False)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Распределение групп по аудиториям и парам")
        self.resize(1200, 950)

        self.db = DB("schedule.db")
        self._last_context: dict | None = None
        self._last_result: distributor.DistributionResult | None = None

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        excel_bar = QHBoxLayout()
        excel_bar.addStretch(1)
        self.btn_export_excel = QPushButton("Экспорт в Excel")
        self.btn_export_excel.setToolTip("Выгрузить все данные в файл .xlsx")
        self.btn_export_excel.clicked.connect(self.export_excel)
        excel_bar.addWidget(self.btn_export_excel)
        self.btn_import_excel = QPushButton("Импорт из Excel")
        self.btn_import_excel.setToolTip("Загрузить данные из файла .xlsx")
        self.btn_import_excel.clicked.connect(self.import_excel)
        excel_bar.addWidget(self.btn_import_excel)
        layout.addLayout(excel_bar)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_groups = QWidget()
        self.tab_auds = QWidget()
        self.tab_teachers = QWidget()
        self.tab_subjects = QWidget()
        self.tab_distribute = QWidget()
        self.tab_schedule = QWidget()
        self.tab_calendar = CalendarTab(self.db)

        self.tabs.addTab(self.tab_groups, "1. Группы")
        self.tabs.addTab(self.tab_auds, "2. Аудитории")
        self.tabs.addTab(self.tab_teachers, "3. Преподаватели")
        self.tabs.addTab(self.tab_subjects, "4. Предметы")
        self.tabs.addTab(self.tab_distribute, "5. Распределение")
        self.tabs.addTab(self.tab_schedule, "6. Расписание")
        self.tabs.addTab(self.tab_calendar, "7. Таблица")

        self._build_groups_tab()
        self._build_auds_tab()
        self._build_teachers_tab()
        self._build_subjects_tab()
        self._build_distribute_tab()
        self._build_schedule_tab()

        self.setLayout(layout)

        self.reload_groups()
        self.reload_auditoriums()
        self.reload_teachers()
        self.reload_subjects()
        self.reload_courses()
        self.reload_schedule_teachers()


    # ГРУППЫ

    def _build_groups_tab(self):
        v = QVBoxLayout()
        self.tab_groups.setLayout(v)

        box = QGroupBox("Добавить группу")
        form = QHBoxLayout()
        form.addWidget(QLabel("Название:"))
        self.g_name = QLineEdit()
        self.g_name.setPlaceholderText("")
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

        v.addWidget(QLabel("Список групп:"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Группа", "Кол-во людей", "Курс"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 80)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.table.itemChanged.connect(self.on_group_item_changed)
        v.addWidget(self.table)

        btns = QHBoxLayout()
        del_btn = QPushButton("Удалить выбранную")
        del_btn.clicked.connect(self.delete_selected_group)
        reload_btn = QPushButton("Обновить из БД")
        reload_btn.clicked.connect(self.refresh_groups_ui)
        clear_btn = QPushButton("Очистить все группы")
        clear_btn.clicked.connect(self.clear_groups)
        btns.addWidget(del_btn)
        btns.addStretch()
        btns.addWidget(reload_btn)
        btns.addWidget(clear_btn)
        v.addLayout(btns)

    def reload_groups(self):
        with signals_blocked(self.table):
            self.table.setRowCount(0)
            for g in self.db.get_groups():
                r = self.table.rowCount()
                self.table.insertRow(r)
                item = QTableWidgetItem(str(g["name"]))
                item.setData(Qt.ItemDataRole.UserRole, int(g["id"]))
                self.table.setItem(r, 0, item)
                self.table.setItem(r, 1, QTableWidgetItem(str(g["students"])))
                self.table.setItem(r, 2, QTableWidgetItem(str(g["course"])))
            self.table.clearSelection()

    def refresh_groups_ui(self):
        self.reload_groups()
        if hasattr(self, "course_combo"):
            self.reload_courses()

    def on_group_item_changed(self, item):

        row = item.row()
        id_item = self.table.item(row, 0)
        if id_item is None:
            return
        gid = id_item.data(Qt.ItemDataRole.UserRole)
        if gid is None:
            return

        name_item = self.table.item(row, 0)
        students_item = self.table.item(row, 1)
        course_item = self.table.item(row, 2)
        if name_item is None or students_item is None or course_item is None:
            return

        name = name_item.text().strip()
        try:
            students = int(students_item.text())
            course = int(course_item.text())
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Студенты и курс должны быть целыми числами.")
            self.reload_groups()
            return

        if not name:
            QMessageBox.warning(self, "Ошибка", "Название группы не может быть пустым.")
            self.reload_groups()
            return
        if students <= 0:
            QMessageBox.warning(self, "Ошибка", "Количество студентов должно быть > 0.")
            self.reload_groups()
            return
        if not (1 <= course <= 6):
            QMessageBox.warning(self, "Ошибка", "Курс должен быть от 1 до 6.")
            self.reload_groups()
            return

        try:
            self.db.update_group(int(gid), name, students, course)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            self.reload_groups()
            return

        # Обновим список курсов и предпросмотр на вкладке распределения
        self.reload_courses()

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


    #  АУДИТОРИИ

    def _build_auds_tab(self):
        v = QVBoxLayout()
        self.tab_auds.setLayout(v)

        box = QGroupBox("Добавить аудиторию")
        form = QHBoxLayout()
        form.addWidget(QLabel("Название:"))
        self.a_name = QLineEdit()
        self.a_name.setPlaceholderText("")
        form.addWidget(self.a_name, 3)
        form.addWidget(QLabel("Вместимость:"))
        self.a_capacity = QSpinBox(minimum=1, maximum=10000, value=25)
        form.addWidget(self.a_capacity)
        form.addWidget(QLabel("Тип:"))
        self.a_kind = QComboBox()
        self.a_kind.addItem("Лекция", KIND_LECTURE)
        self.a_kind.addItem("Практика", KIND_PRACTICE)
        form.addWidget(self.a_kind)
        btn = QPushButton("Добавить")
        btn.clicked.connect(self.add_auditorium)
        form.addWidget(btn)
        box.setLayout(form)
        v.addWidget(box)

        v.addWidget(QLabel("Список аудиторий:"))
        self.aud_table = QTableWidget(0, 3)
        self.aud_table.setHorizontalHeaderLabels(["Аудитория", "Вместимость", "Тип"])
        self.aud_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.aud_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.aud_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.aud_table.setColumnWidth(1, 120)
        self.aud_table.setColumnWidth(2, 160)
        self.aud_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.aud_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.aud_table.itemChanged.connect(self.on_aud_item_changed)
        v.addWidget(self.aud_table)

        btns = QHBoxLayout()
        del_btn = QPushButton("Удалить выбранную")
        del_btn.clicked.connect(self.delete_selected_aud)
        reload_btn = QPushButton("Обновить из БД")
        reload_btn.clicked.connect(self.refresh_auds_ui)
        clear_btn = QPushButton("Очистить все аудитории")
        clear_btn.clicked.connect(self.clear_auditoriums)
        btns.addWidget(del_btn)
        btns.addStretch()
        btns.addWidget(reload_btn)
        btns.addWidget(clear_btn)
        v.addLayout(btns)

    def reload_auditoriums(self):
        with signals_blocked(self.aud_table):
            self.aud_table.setRowCount(0)
            for a in self.db.get_auditoriums():
                r = self.aud_table.rowCount()
                self.aud_table.insertRow(r)
                item = QTableWidgetItem(str(a.name))
                item.setData(Qt.ItemDataRole.UserRole, int(a.id))
                self.aud_table.setItem(r, 0, item)
                self.aud_table.setItem(r, 1, QTableWidgetItem(str(a.capacity)))

                combo = QComboBox()
                combo.addItem("Лекция", KIND_LECTURE)
                combo.addItem("Практика", KIND_PRACTICE)
                combo.setCurrentIndex(0 if a.kind == KIND_LECTURE else 1)
                combo.currentIndexChanged.connect(
                    lambda _i, aid=a.id, c=combo: self._on_aud_kind_changed(aid, c.currentData())
                )
                self.aud_table.setCellWidget(r, 2, combo)
            self.aud_table.clearSelection()

    def refresh_auds_ui(self):
        self.reload_auditoriums()
        self._reload_aud_for_teacher_combo()
        if hasattr(self, "summary_label"):
            self.on_course_changed()

    def _on_aud_kind_changed(self, aid, kind):
        try:
            self.db.update_auditorium_kind(int(aid), kind)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        if hasattr(self, "summary_label"):
            self.on_course_changed()

    def on_aud_item_changed(self, item):
        if item.column() not in (0, 1):
            return  # тип аудитории обрабатывается отдельно
        row = item.row()
        id_item = self.aud_table.item(row, 0)
        if id_item is None:
            return
        aid = id_item.data(Qt.ItemDataRole.UserRole)
        if aid is None:
            return

        name_item = self.aud_table.item(row, 0)
        cap_item = self.aud_table.item(row, 1)
        if name_item is None or cap_item is None:
            return

        name = name_item.text().strip()
        try:
            capacity = int(cap_item.text())
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Вместимость должна быть целым числом.")
            self.reload_auditoriums()
            return

        if not name:
            QMessageBox.warning(self, "Ошибка", "Название аудитории не может быть пустым.")
            self.reload_auditoriums()
            return
        if capacity <= 0:
            QMessageBox.warning(self, "Ошибка", "Вместимость должна быть > 0.")
            self.reload_auditoriums()
            return

        try:
            self.db.update_auditorium(int(aid), name, capacity)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            self.reload_auditoriums()
            return

        self._reload_aud_for_teacher_combo()
        if hasattr(self, "summary_label"):
            self.on_course_changed()

    def add_auditorium(self):
        name = self.a_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название аудитории.")
            return
        try:
            self.db.add_auditorium(name, self.a_capacity.value(), self.a_kind.currentData())
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.a_name.clear()
        self.reload_auditoriums()
        self._reload_aud_for_teacher_combo()
        if hasattr(self, "summary_label"):
            self.on_course_changed()

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
        self._reload_aud_for_teacher_combo()
        self.on_teacher_selected()

    def clear_auditoriums(self):
        if QMessageBox.question(self, "Очистка", "Удалить ВСЕ аудитории?") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.clear_auditoriums()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
        self.reload_auditoriums()
        self._reload_aud_for_teacher_combo()
        self.on_teacher_selected()


    #  ПРЕПОДАВАТЕЛИ

    def _build_teachers_tab(self):
        v = QVBoxLayout()
        self.tab_teachers.setLayout(v)

        box = QGroupBox("Добавить преподавателя")
        form = QHBoxLayout()
        form.addWidget(QLabel("Имя:"))
        self.t_name = QLineEdit()
        self.t_name.setPlaceholderText("")
        form.addWidget(self.t_name, 1)
        btn = QPushButton("Добавить")
        btn.clicked.connect(self.add_teacher)
        form.addWidget(btn)
        box.setLayout(form)
        v.addWidget(box)

        h = QHBoxLayout()

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

        mid = QVBoxLayout()
        mid.addWidget(QLabel("Предметы преподавателя:"))
        self.teacher_subjects_table = QTableWidget(0, 1)
        self.teacher_subjects_table.setHorizontalHeaderLabels(["Предмет"])
        self.teacher_subjects_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.teacher_subjects_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        mid.addWidget(self.teacher_subjects_table)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Привязать:"))
        self.subj_for_teacher_combo = QComboBox()
        row1.addWidget(self.subj_for_teacher_combo, 1)
        btn1 = QPushButton("Привязать")
        btn1.clicked.connect(self.assign_subject_to_teacher)
        row1.addWidget(btn1)
        mid.addLayout(row1)

        unassign_subj = QPushButton("Отвязать выбранный предмет")
        unassign_subj.clicked.connect(self.unassign_subject_from_teacher)
        mid.addWidget(unassign_subj)

        right = QVBoxLayout()
        right.addWidget(QLabel("Аудитории преподавателя:"))
        self.teacher_auds_table = QTableWidget(0, 2)
        self.teacher_auds_table.setHorizontalHeaderLabels(["Аудитория", "Тип"])
        self.teacher_auds_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.teacher_auds_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.teacher_auds_table.setColumnWidth(1, 100)
        self.teacher_auds_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        right.addWidget(self.teacher_auds_table)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Привязать:"))
        self.aud_for_teacher_combo = QComboBox()
        row2.addWidget(self.aud_for_teacher_combo, 1)
        btn2 = QPushButton("Привязать")
        btn2.clicked.connect(self.assign_auditorium_to_teacher)
        row2.addWidget(btn2)
        right.addLayout(row2)

        unassign_aud = QPushButton("Отвязать выбранную аудиторию")
        unassign_aud.clicked.connect(self.unassign_auditorium_from_teacher)
        right.addWidget(unassign_aud)

        h.addLayout(left, 1)
        h.addLayout(mid, 1)
        h.addLayout(right, 1)
        v.addLayout(h)

    def reload_teachers(self):
        with signals_blocked(self.teachers_table):
            self.teachers_table.setRowCount(0)
            for t in self.db.get_teachers():
                r = self.teachers_table.rowCount()
                self.teachers_table.insertRow(r)
                item = QTableWidgetItem(str(t["name"]))
                item.setData(Qt.ItemDataRole.UserRole, int(t["id"]))
                self.teachers_table.setItem(r, 0, item)
            self.teachers_table.clearSelection()
        self.teacher_subjects_table.setRowCount(0)
        self.teacher_auds_table.setRowCount(0)
        self._reload_subj_for_teacher_combo()
        self._reload_aud_for_teacher_combo()
        # Обновляем вкладку 5: новый преподаватель должен появиться в комбобоксе
        if hasattr(self, "subject_combo"):
            self.on_subject_changed()

    def _reload_subj_for_teacher_combo(self):
        self.subj_for_teacher_combo.clear()
        for s in self.db.get_subjects():
            self.subj_for_teacher_combo.addItem(str(s["name"]), int(s["id"]))

    def _reload_aud_for_teacher_combo(self):
        if not hasattr(self, "aud_for_teacher_combo"):
            return
        self.aud_for_teacher_combo.clear()
        for a in self.db.get_auditoriums():
            self.aud_for_teacher_combo.addItem(
                f"{a.name} ({KIND_LABELS.get(a.kind, a.kind)})", int(a.id)
            )

    def on_teacher_selected(self):
        with signals_blocked(self.teacher_subjects_table):
            self.teacher_subjects_table.setRowCount(0)
            row = self.teachers_table.currentRow()
            if row < 0:
                self.teacher_auds_table.setRowCount(0)
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

        with signals_blocked(self.teacher_auds_table):
            self.teacher_auds_table.setRowCount(0)
            for a in self.db.get_auditoriums_of_teacher(int(tid)):
                r = self.teacher_auds_table.rowCount()
                self.teacher_auds_table.insertRow(r)
                it = QTableWidgetItem(str(a.name))
                it.setData(Qt.ItemDataRole.UserRole, int(a.id))
                self.teacher_auds_table.setItem(r, 0, it)
                self.teacher_auds_table.setItem(r, 1, QTableWidgetItem(KIND_LABELS.get(a.kind, a.kind)))

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
        self.reload_schedule_teachers()

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
        self.reload_schedule_teachers()

    def assign_subject_to_teacher(self):
        tid = self._selected_teacher_id()
        if tid is None:
            QMessageBox.warning(self, "Ошибка", "Выберите преподавателя слева.")
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
        self.on_subject_changed()

    def unassign_subject_from_teacher(self):
        tid = self._selected_teacher_id()
        if tid is None:
            return
        srow = self.teacher_subjects_table.currentRow()
        if srow < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите предмет посередине.")
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
        self.on_subject_changed()

    def assign_auditorium_to_teacher(self):
        tid = self._selected_teacher_id()
        if tid is None:
            QMessageBox.warning(self, "Ошибка", "Выберите преподавателя слева.")
            return
        aid = self.aud_for_teacher_combo.currentData()
        if aid is None:
            QMessageBox.warning(self, "Ошибка", "Нет доступных аудиторий.")
            return
        try:
            self.db.assign_teacher_auditorium(int(tid), int(aid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.on_teacher_selected()

    def unassign_auditorium_from_teacher(self):
        tid = self._selected_teacher_id()
        if tid is None:
            return
        arow = self.teacher_auds_table.currentRow()
        if arow < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите аудиторию справа.")
            return
        aitem = self.teacher_auds_table.item(arow, 0)
        if aitem is None:
            return
        aid = aitem.data(Qt.ItemDataRole.UserRole)
        if aid is None:
            return
        try:
            self.db.unassign_teacher_auditorium(int(tid), int(aid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.on_teacher_selected()

    def _selected_teacher_id(self):
        row = self.teachers_table.currentRow()
        if row < 0:
            return None
        item = self.teachers_table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)


    # ПРЕДМЕТЫ

    def _build_subjects_tab(self):
        v = QVBoxLayout()
        self.tab_subjects.setLayout(v)

        box = QGroupBox("Добавить предмет")
        form = QHBoxLayout()
        form.addWidget(QLabel("Название:"))
        self.s_name = QLineEdit()
        self.s_name.setPlaceholderText("")
        form.addWidget(self.s_name, 1)
        btn = QPushButton("Добавить")
        btn.clicked.connect(self.add_subject)
        form.addWidget(btn)
        box.setLayout(form)
        v.addWidget(box)

        h = QHBoxLayout()

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

        right = QVBoxLayout()
        right.addWidget(QLabel("Привязанные курсы"))
        self.subject_courses_table = QTableWidget(0, 1)
        self.subject_courses_table.setHorizontalHeaderLabels(["Курс"])
        self.subject_courses_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.subject_courses_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        right.addWidget(self.subject_courses_table)

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
        with signals_blocked(self.subjects_table):
            self.subjects_table.setRowCount(0)
            for s in self.db.get_subjects():
                r = self.subjects_table.rowCount()
                self.subjects_table.insertRow(r)
                item = QTableWidgetItem(str(s["name"]))
                item.setData(Qt.ItemDataRole.UserRole, int(s["id"]))
                self.subjects_table.setItem(r, 0, item)
            self.subjects_table.clearSelection()
        self.subject_courses_table.setRowCount(0)
        self._reload_subj_for_teacher_combo()
        # Обновляем вкладку 5: новый предмет должен появиться в комбобоксе
        if hasattr(self, "course_combo"):
            self.on_course_changed()

    def on_subject_selected(self):
        with signals_blocked(self.subject_courses_table):
            self.subject_courses_table.setRowCount(0)
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
        sid = self._selected_subject_id()
        if sid is None:
            QMessageBox.warning(self, "Ошибка", "Выберите предмет слева.")
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
        sid = self._selected_subject_id()
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

    def _selected_subject_id(self):
        row = self.subjects_table.currentRow()
        if row < 0:
            return None
        item = self.subjects_table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)


    # РАСПРЕДЕЛЕНИЕ ПО ПАРАМ

    def _build_distribute_tab(self):
        v = QVBoxLayout()
        self.tab_distribute.setLayout(v)

        sel_box = QGroupBox("Параметры распределения")
        form = QFormLayout()
        self.course_combo = QComboBox()
        self.subject_combo = QComboBox()
        self.teacher_combo = QComboBox()
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Лекция", KIND_LECTURE)
        self.kind_combo.addItem("Практика", KIND_PRACTICE)

        form.addRow(QLabel("Курс:"), self.course_combo)
        form.addRow(QLabel("Предмет:"), self.subject_combo)
        form.addRow(QLabel("Преподаватель:"), self.teacher_combo)
        form.addRow(QLabel("Тип занятия:"), self.kind_combo)
        self.max2_checkbox = QCheckBox("Не больше 2 лекций в день")
        self.max2_checkbox.setToolTip(
            "При генерации лекции преподавателя раскладываются по дням Пн–Пт "
            "так, чтобы в один день было не больше 2 лекций "
            "(учитывается уже записанное расписание). Действует только для лекций."
        )
        form.addRow(QLabel("Фильтр:"), self.max2_checkbox)
        sel_box.setLayout(form)
        v.addWidget(sel_box)

        self.course_combo.currentIndexChanged.connect(self.on_course_changed)
        self.subject_combo.currentIndexChanged.connect(self.on_subject_changed)
        self.teacher_combo.currentIndexChanged.connect(self.on_teacher_for_dist_changed)
        self.kind_combo.currentIndexChanged.connect(self.on_kind_changed)
        self.max2_checkbox.toggled.connect(self.on_max2_changed)

        gbox = QGroupBox("Группы")
        gv = QVBoxLayout()
        self.groups_preview = QTableWidget(0, 3)
        self.groups_preview.setHorizontalHeaderLabels(["", "Группа", "Человек"])
        hh = self.groups_preview.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.groups_preview.setColumnWidth(0, 40)
        self.groups_preview.setColumnWidth(2, 100)
        self.groups_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.groups_preview.setMaximumHeight(200)
        gv.addWidget(self.groups_preview)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #9aa;")
        gv.addWidget(self.summary_label)
        gbox.setLayout(gv)
        v.addWidget(gbox)

        btns = QHBoxLayout()
        run_btn = QPushButton("Распределить по ячейкам")
        run_btn.setStyleSheet(
            "QPushButton { font-weight: bold; background-color: #2e7d32; "
            "padding: 10px 16px; font-size: 14px; }"
            "QPushButton:hover { background-color: #388e3c; }"
        )
        run_btn.clicked.connect(self.distribute)
        btns.addWidget(run_btn, 2)

        save_btn = QPushButton("Записать в расписание")
        save_btn.setStyleSheet(
            "QPushButton { font-weight: bold; background-color: #1565c0; "
            "padding: 10px 16px; font-size: 14px; }"
            "QPushButton:hover { background-color: #1976d2; }"
        )
        save_btn.clicked.connect(self.write_to_schedule)
        btns.addWidget(save_btn, 2)
        v.addLayout(btns)

        # --- Одна длинная кнопка «Распределить и записать» ---
        auto_btn = QPushButton("Распределить и сразу записать в расписание")
        auto_btn.setStyleSheet(
            "QPushButton { font-weight: bold; background-color: #FF0000; "
            "padding: 6px 12px; font-size: 13px; }"
            "QPushButton:hover { background-color: #FF4040; }"
        )
        auto_btn.setMinimumHeight(28)
        auto_btn.clicked.connect(self.distribute_and_write)
        v.addWidget(auto_btn)

        rbox = QGroupBox("Результат")
        rv = QVBoxLayout()
        self.toggle_btn = QPushButton("Показать текст")
        self.toggle_btn.clicked.connect(self.toggle_result_mode)
        rv.addWidget(self.toggle_btn)

        self.result_container = QFrame()
        res_layout = QVBoxLayout()
        res_layout.setContentsMargins(4, 4, 4, 4)
        self.result_container.setLayout(res_layout)

        self.text_result = QTextEdit()
        self.text_result.setReadOnly(True)
        self.text_result.setMinimumHeight(240)
        self.text_result.setVisible(False)  # ← по умолчанию скрыт
        res_layout.addWidget(self.text_result)

        self.table_result = QTableWidget()
        self.table_result.setVisible(True)
        self.table_result.setColumnCount(6)
        self.table_result.setHorizontalHeaderLabels(
            ["Ячейка", "Аудитория", "Группы", "Человек", "Заполнено", "Прогресс"]
        )
        header = self.table_result.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table_result.setColumnWidth(0, 80)
        self.table_result.setColumnWidth(1, 120)
        self.table_result.setColumnWidth(3, 90)
        self.table_result.setColumnWidth(4, 110)
        self.table_result.setColumnWidth(5, 90)
        res_layout.addWidget(self.table_result)

        rv.addWidget(self.result_container)
        rbox.setLayout(rv)
        v.addWidget(rbox)

    def reload_courses(self):
        prev_course = self.course_combo.currentData()
        prev_subject = self.subject_combo.currentData()
        with signals_blocked(self.course_combo):
            self.course_combo.clear()
            courses = sorted({g["course"] for g in self.db.get_groups()})
            for n in courses:
                self.course_combo.addItem(f"{n} курс", int(n))
            if not courses:
                self.course_combo.addItem("— нет групп —", None)
            elif prev_course is not None:
                idx = self.course_combo.findData(int(prev_course))
                if idx >= 0:
                    self.course_combo.setCurrentIndex(idx)
        self.on_course_changed(keep_subject=prev_subject)

    def on_course_changed(self, _idx=None, keep_subject=None):
        course = self.course_combo.currentData()
        if course is None:
            with signals_blocked(self.subject_combo):
                self.subject_combo.clear()
                self.subject_combo.addItem("— нет предметов —", None)
            with signals_blocked(self.teacher_combo):
                self.teacher_combo.clear()
                self.teacher_combo.addItem("— не выбран —", None)
            self.groups_preview.setRowCount(0)
            self.summary_label.setText("")
            self.text_result.setText(
                "Нет групп. Добавьте группы на вкладке «1. Группы»."
            )
            self.table_result.setRowCount(0)
            self._show_result_text()
            return

        prev_sid = keep_subject if keep_subject is not None else self.subject_combo.currentData()
        with signals_blocked(self.subject_combo):
            self.subject_combo.clear()
            subjects = self.db.get_course_subjects(int(course))
            for s in subjects:
                self.subject_combo.addItem(str(s["name"]), int(s["id"]))
            if not subjects:
                self.subject_combo.addItem("— нет предметов у курса —", None)
            elif prev_sid is not None:
                idx = self.subject_combo.findData(int(prev_sid))
                if idx >= 0:
                    self.subject_combo.setCurrentIndex(idx)

        with signals_blocked(self.groups_preview):
            self.groups_preview.setRowCount(0)
            groups = self.db.get_groups_by_course(int(course))
            for g in groups:
                r = self.groups_preview.rowCount()
                self.groups_preview.insertRow(r)
                chk = QTableWidgetItem()
                chk.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                )
                chk.setCheckState(Qt.CheckState.Checked)
                chk.setData(Qt.ItemDataRole.UserRole, int(g.id))
                self.groups_preview.setItem(r, 0, chk)
                self.groups_preview.setItem(r, 1, QTableWidgetItem(str(g.name)))
                self.groups_preview.setItem(r, 2, QTableWidgetItem(str(g.students)))

        self.on_subject_changed()

    def on_subject_changed(self, _idx=None, keep_teacher=None):
        sid = self.subject_combo.currentData()
        prev_tid = keep_teacher if keep_teacher is not None else self.teacher_combo.currentData()
        teachers: list[dict] = []
        if sid is not None:
            teachers = self.db.get_teachers_of_subject(int(sid))
        with signals_blocked(self.teacher_combo):
            self.teacher_combo.clear()
            self.teacher_combo.addItem("— не выбран —", None)
            for t in teachers:
                self.teacher_combo.addItem(str(t["name"]), int(t["id"]))
            if prev_tid is not None:
                idx = self.teacher_combo.findData(int(prev_tid))
                if idx >= 0:
                    self.teacher_combo.setCurrentIndex(idx)

        self._last_context = None
        self._last_result = None

        if sid is None:
            self.text_result.setText(
                "Для этого курса ещё нет привязанных предметов.\n"
                "Перейдите на вкладку «4. Предметы» и привяжите предмет к курсу."
            )
            self.table_result.setRowCount(0)
            self._refresh_auditorium_summary()
            self._show_result_text()
            return

        saved = self.db.load_distribution(int(sid))
        if saved:
            lines = [f"Ранее сохранённое распределение для «{self.subject_combo.currentText()}»:"]
            by_pair: dict[int, list[dict]] = {}
            for r in saved:
                by_pair.setdefault(r["pair_number"], []).append(r)
            for pair in sorted(by_pair):
                lines.append("")
                lines.append(f"Пара {pair}:")
                for r in by_pair[pair]:
                    lines.append(
                        f"  {r['aud_name']}: {r['grp_name']} ({r['students']} чел.)"
                    )
            self.text_result.setText("\n".join(lines))
        else:
            self.text_result.setText(
                f"Для предмета «{self.subject_combo.currentText()}» распределения ещё нет.\n"
                f"Настройте параметры и нажмите «Распределить по парам»."
            )
        if not teachers:
            self.text_result.setText(
                self.text_result.toPlainText()
                + "\n\nК предмету не привязан ни один преподаватель.\n"
                + "Откройте вкладку «3. Преподаватели» и нажмите «Привязать»."
            )
        self.table_result.setRowCount(0)
        self._refresh_auditorium_summary()
        self._show_result_text()

    def on_teacher_for_dist_changed(self):
        self._last_context = None
        self._last_result = None
        self._refresh_auditorium_summary()

    def on_kind_changed(self):
        self._last_context = None
        self._last_result = None
        if hasattr(self, "max2_checkbox"):
            is_lecture = self.kind_combo.currentData() == KIND_LECTURE
            self.max2_checkbox.setEnabled(is_lecture)
            if not is_lecture:
                self.max2_checkbox.setChecked(False)
        self._refresh_auditorium_summary()

    def on_max2_changed(self):
        self._last_context = None
        self._last_result = None
        self._refresh_auditorium_summary()

    def _refresh_auditorium_summary(self):
        course = self.course_combo.currentData()
        if course is None:
            return
        kind = self.kind_combo.currentData()
        all_auds = self.db.get_auditoriums()
        by_kind = [a for a in all_auds if a.kind == kind]

        teacher_id = self.teacher_combo.currentData()
        note = ""
        if teacher_id is not None:
            linked = self.db.get_auditoriums_of_teacher(int(teacher_id))
            linked_ids = {a.id for a in linked}
            linked_kind = [a for a in by_kind if a.id in linked_ids]
            if linked_kind:
                note = f"  ·  у препода: {len(linked_kind)}"
            else:
                note = "  ·  у препода нет своих аудиторий, беру все"

        checked = sum(
            1 for r in range(self.groups_preview.rowCount())
            if self.groups_preview.item(r, 0)
            and self.groups_preview.item(r, 0).checkState() == Qt.CheckState.Checked
        )
        total = self.groups_preview.rowCount()

        # Сколько мест/ячеек понадобится хотя бы теоретически
        cells_hint = ""
        if checked > 0 and len(by_kind) > 0:
            people = sum(
                int(self.groups_preview.item(r, 2).text())
                for r in range(self.groups_preview.rowCount())
                if self.groups_preview.item(r, 0)
                and self.groups_preview.item(r, 0).checkState() == Qt.CheckState.Checked
                and self.groups_preview.item(r, 2) is not None
            )
            if kind == KIND_LECTURE:
                # Весь поток в одну аудиторию
                biggest = max(a.capacity for a in by_kind)
                if biggest >= people:
                    cells_hint = f"  ·  поток {people} чел. — 1 ячейка"
                else:
                    cells_hint = (
                        f"  ·  поток {people} чел. не влезет "
                        f"(максимум {biggest})!"
                    )
            else:
                # Практика: не больше 2 групп в кабинете
                need = -(-checked // (2 * len(by_kind)))  # ceil
                cells_hint = f"  ·  ячеек нужно минимум: {need} (по 2 группы)"

        self.summary_label.setText(
            f"Групп выбрано: {checked} из {total}  ·  "
            f"Аудиторий типа «{KIND_LABELS[kind]}»: {len(by_kind)}{note}{cells_hint}"
            f"{self._day_loads_hint(teacher_id, kind)}"
        )

    def _day_loads_hint(self, teacher_id, kind) -> str:
        """Подсказка для фильтра: сколько лекций уже стоит у препода по дням."""
        if not getattr(self, "max2_checkbox", None):
            return ""
        if not self.max2_checkbox.isChecked() or kind != KIND_LECTURE:
            return ""
        if teacher_id is None:
            return "  ·  фильтр: выберите преподавателя"
        try:
            rows = self.db.get_teacher_schedule(int(teacher_id))
        except Exception:
            return ""
        loads = [0] * 5
        for r in rows:
            if r.get("kind") != KIND_LECTURE:
                continue
            try:
                w = int(r.get("weekday", 0) or 0)
            except (TypeError, ValueError):
                w = 0
            if 0 <= w <= 4:
                loads[w] += 1
        return "  ·  лекций по дням Пн–Пт: " + "/".join(str(n) for n in loads)

    def _show_result_text(self):
        self.text_result.setVisible(True)
        self.table_result.setVisible(False)
        self.toggle_btn.setText("Показать таблицу")

    def _show_result_table(self):
        self.text_result.setVisible(False)
        self.table_result.setVisible(True)
        self.toggle_btn.setText("Показать текст")

    def toggle_result_mode(self):
        if self.table_result.isVisible():
            self._show_result_text()
        else:
            self._show_result_table()

    MAX_LECTURES_PER_DAY = 2

    def _assign_weekdays(
        self, result: distributor.DistributionResult, teacher_id: int,
        subject_id: int, kind: str, max_per_day: int | None = None,
    ) -> str:
        """Раскладывает result.placed по дням Пн–Пт (поле weekday).

        Единица планирования — связка (пара + аудитория): все группы одного
        занятия получают один день, поток не разбивается. Связка кладётся
        только на день, где эта пара у преподавателя свободна или занята
        ТЕМ ЖЕ занятием (тогда запись сольётся/пропустит дубли). Занятия,
        для которых нет свободного дня, переносятся в not_placed целиком —
        накладка невозможна по построению.
        max_per_day ограничивает число новых занятий в день (фильтр лекций).
        Возвращает заметку для отчёта ("" если всё поместилось).
        """
        existing = self.db.get_teacher_schedule(int(teacher_id))
        loads = [0] * 5
        # (день, пара) -> множество ключей занятий, уже стоящих там
        busy: dict[tuple[int, int], set[tuple]] = {}
        for r in existing:
            try:
                w = int(r.get("weekday", 0) or 0)
            except (TypeError, ValueError):
                w = 0
            if not 0 <= w <= 4:
                continue
            try:
                p = int(r.get("pair_number", 0) or 0)
            except (TypeError, ValueError):
                p = 0
            if not p:
                continue
            sid = -1 if r.get("subject_id") is None else int(r["subject_id"])
            busy.setdefault((w, p), set()).add(
                (sid, str(r.get("kind")), str(r.get("aud_name") or "")))
            if max_per_day is not None and r.get("kind") == KIND_LECTURE:
                loads[w] += 1

        overflow: list[distributor.Group] = []
        kept: list[distributor.PlacedGroup] = []
        bundles: dict[tuple[int, int], list[distributor.PlacedGroup]] = {}
        for p in result.placed:
            bundles.setdefault((p.cell, p.auditorium.id), []).append(p)
        for (cell, aid) in sorted(bundles):
            bundle = bundles[(cell, aid)]
            my_key = (int(subject_id), str(kind), str(bundle[0].auditorium.name))
            # Кандидаты: дни, где пара свободна или занята тем же занятием.
            # Сначала дни с тем же занятием (перезапись сольётся),
            # потом наименее загруженные.
            cands = []
            for w in range(5):
                holders = busy.get((w, cell), set())
                foreign = {h for h in holders if h != my_key}
                if foreign:
                    continue
                if max_per_day is not None and loads[w] >= max_per_day:
                    continue
                same = bool(holders)  # там уже стоит это же занятие
                cands.append((loads[w] if max_per_day is not None else 0,
                              0 if same else 1, w))
            if not cands:
                overflow.extend(p.group for p in bundle)
                continue
            chosen = sorted(cands)[0][2]
            for p in bundle:
                p.weekday = chosen
                kept.append(p)
            busy.setdefault((chosen, cell), set()).add(my_key)
            if max_per_day is not None:
                loads[chosen] += 1

        result.placed = kept
        result.not_placed = list(result.not_placed) + overflow

        if not overflow:
            return ""
        names = ", ".join(g.name for g in overflow)
        if max_per_day is not None:
            return (
                f"Лимит «не больше {max_per_day} лекций в день»: "
                f"не поместились ({len(overflow)}): {names}"
            )
        return (
            f"Пара занята у преподавателя всю неделю: "
            f"не поместились ({len(overflow)}): {names}"
        )

    def distribute(self, silent: bool = False) -> bool:
        course = self.course_combo.currentData()
        subject_id = self.subject_combo.currentData()
        kind = self.kind_combo.currentData()
        teacher_id = self.teacher_combo.currentData()

        if course is None or subject_id is None:
            if not silent:
                QMessageBox.warning(self, "Ошибка", "Сначала выберите курс и предмет.")
            return False

        groups: list[distributor.Group] = []
        for r in range(self.groups_preview.rowCount()):
            chk = self.groups_preview.item(r, 0)
            if chk is None or chk.checkState() != Qt.CheckState.Checked:
                continue
            gid = chk.data(Qt.ItemDataRole.UserRole)
            name_item = self.groups_preview.item(r, 1)
            people_item = self.groups_preview.item(r, 2)
            groups.append(distributor.Group(
                id=int(gid),
                name=name_item.text(),
                students=int(people_item.text()),
            ))

        if not groups:
            if not silent:
                QMessageBox.warning(self, "Ошибка", "Не выбрано ни одной группы.")
            return False

        all_auds = self.db.get_auditoriums()
        auds = [a for a in all_auds if a.kind == kind]

        if teacher_id is not None:
            linked = self.db.get_auditoriums_of_teacher(int(teacher_id))
            linked_ids = {a.id for a in linked}
            restricted = [a for a in auds if a.id in linked_ids]
            if restricted:
                auds = restricted

        if not auds:
            if not silent:
                QMessageBox.warning(
                    self, "Ошибка",
                    f"Нет аудиторий типа «{KIND_LABELS[kind]}» для распределения."
                )
            return False

        result = distributor.distribute(
            groups, auds,
            time_per_cell=1.0,
            # Лекция — весь поток вместе; практика — не больше 2 групп в кабинете
            whole_stream=(kind == KIND_LECTURE),
            max_groups_per_room=None if kind == KIND_LECTURE else 2,
        )

        use_max2 = (
            getattr(self, "max2_checkbox", None) is not None
            and self.max2_checkbox.isChecked()
            and kind == KIND_LECTURE
        )
        if use_max2 and teacher_id is None:
            if not silent:
                QMessageBox.warning(
                    self, "Ошибка",
                    "Для фильтра «Не больше 2 лекций в день» выберите преподавателя."
                )
            return False
        # Дни назначаются всегда, когда выбран преподаватель: каждая связка
        # (пара + аудитория) кладётся на день, свободный у преподавателя.
        # Без преподавателя дни неизвестны — остаётся Пн (запись всё равно
        # потребует преподавателя).
        days_note = ""
        with_days = teacher_id is not None
        if with_days:
            days_note = self._assign_weekdays(
                result, int(teacher_id), int(subject_id), kind,
                max_per_day=self.MAX_LECTURES_PER_DAY if use_max2 else None,
            )

        self._last_result = result
        self._last_context = {
            "course": int(course),
            "subject_id": int(subject_id),
            "teacher_id": int(teacher_id) if teacher_id is not None else None,
            "kind": kind,
            "with_days": with_days,
            "limit_note": days_note,
        }

        assignments = [(p.group.id, p.auditorium.id, p.cell) for p in result.placed]
        try:
            self.db.save_distribution(int(subject_id), assignments)
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Ошибка сохранения", str(e))

        self._render_text_result(course, result)
        self._render_table_result(result)
        return True

    def _render_text_result(self, course: int, result: distributor.DistributionResult):
        ctx = self._last_context or {}
        kind = ctx.get("kind", KIND_LECTURE)
        with_days = bool(ctx.get("with_days"))
        teacher_name = self.teacher_combo.currentText() if self.teacher_combo.currentData() else "—"

        total_groups = len(result.placed) + len(result.not_placed)
        lines = [
            f"Курс {course}, предмет: {self.subject_combo.currentText()}",
            f"Преподаватель: {teacher_name}",
            f"Тип занятия: {KIND_LABELS.get(kind, kind)}",
            f"Групп размещено: {len(result.placed)} из {total_groups}",
            f"Использовано ячеек: {result.cells_used}",
            f"Всего человек: {result.total_people}",
        ]
        if with_days:
            lines.append(
                f"Фильтр: не больше {self.MAX_LECTURES_PER_DAY} лекций в день — вкл."
            )
        if result.note:
            lines.append(result.note)

        if with_days:
            slots: dict[tuple[int, int], list[distributor.PlacedGroup]] = {}
            for p in result.placed:
                slots.setdefault((p.weekday, p.cell), []).append(p)
            for (w, cell) in sorted(slots):
                lines.append("")
                lines.append(f"{WEEKDAYS[w]} · Пара {cell}:")
                for p in sorted(slots[(w, cell)], key=lambda x: x.auditorium.name):
                    aud = p.auditorium
                    lines.append(
                        f"  {aud.name} [{p.group.students}/{aud.capacity}]: "
                        f"{p.group.name} ({p.group.students} чел.)"
                    )
        else:
            cells = result.cells()
            for cell in sorted({c for (c, _a) in cells}):
                lines.append("")
                lines.append(f"Ячейка {cell}:")
                cell_cells = sorted(
                    [(aid, lst) for (c, aid), lst in cells.items() if c == cell],
                    key=lambda kv: kv[1][0].auditorium.name,
                )
                for _aid, lst in cell_cells:
                    aud = lst[0].auditorium
                    people = sum(x.group.students for x in lst)
                    free = aud.capacity - people
                    names = ", ".join(f"{x.group.name} ({x.group.students})" for x in lst)
                    lines.append(
                        f"  {aud.name} [{people}/{aud.capacity}, свободно {free}]: {names}"
                    )

        if result.not_placed:
            lines.append("")
            if ctx.get("limit_note"):
                lines.append(ctx["limit_note"])
            else:
                lines.append("!!! НЕ ПОМЕСТИЛИСЬ (не хватило ячеек) !!!")
            for g in result.not_placed:
                lines.append(f"- {g.name} ({g.students} чел.)")

        self.text_result.setText("\n".join(lines))

    def _render_table_result(self, result: distributor.DistributionResult):
        ctx = self._last_context or {}
        with_days = bool(ctx.get("with_days"))
        self.table_result.setRowCount(0)
        # Группируем по (пара, аудитория, день), чтобы дни не сливались в одну строку
        grouped: dict[tuple[int, int, int], list[distributor.PlacedGroup]] = {}
        for p in result.placed:
            grouped.setdefault((p.cell, p.auditorium.id, p.weekday), []).append(p)
        ordered = sorted(
            grouped.items(),
            key=lambda kv: (
                kv[0][2] if with_days else 0,
                kv[0][0],
                kv[1][0].auditorium.name,
            ),
        )
        for (_cell, _aid, _w), lst in ordered:
            cell = lst[0].cell
            aud = lst[0].auditorium
            people = sum(x.group.students for x in lst)
            cap = aud.capacity
            names = ", ".join(f"{x.group.name} ({x.group.students})" for x in lst)

            row = self.table_result.rowCount()
            self.table_result.insertRow(row)
            cell_text = f"{cell} · {WEEKDAYS[_w]}" if with_days else str(cell)
            self.table_result.setItem(row, 0, QTableWidgetItem(cell_text))
            self.table_result.setItem(row, 1, QTableWidgetItem(aud.name))
            self.table_result.setItem(row, 2, QTableWidgetItem(names))
            self.table_result.setItem(row, 3, QTableWidgetItem(str(people)))
            self.table_result.setItem(row, 4, QTableWidgetItem(f"{people}/{cap}"))

            w = QWidget()
            bar = QProgressBar()
            bar.setRange(0, cap)
            bar.setValue(people)
            bar.setTextVisible(False)
            l = QHBoxLayout()
            l.setContentsMargins(0, 0, 0, 0)
            l.addWidget(bar)
            w.setLayout(l)
            self.table_result.setCellWidget(row, 5, w)

        if result.not_placed:
            row = self.table_result.rowCount()
            self.table_result.insertRow(row)
            msg = "!!! НЕ ПОМЕСТИЛИСЬ: " + ", ".join(g.name for g in result.not_placed)
            item = QTableWidgetItem(msg)
            item.setForeground(Qt.GlobalColor.red)
            self.table_result.setItem(row, 0, item)
            self.table_result.setSpan(row, 0, 1, 6)

        self._show_result_table()

    def write_to_schedule(self, silent: bool = False):
        if self._last_result is None or self._last_context is None:
            if not silent:
                QMessageBox.warning(
                    self, "Ошибка",
                    "Сначала выполните распределение (кнопка «▶ Распределить по ячейкам»)."
                )
            return (None, None)

        ctx = self._last_context
        if ctx["teacher_id"] is None:
            if not silent:
                QMessageBox.warning(
                    self, "Ошибка",
                    "Не выбран преподаватель.\n"
                    "Выберите преподавателя и повторите распределение."
                )
            return (None, None)

        assignments = [
            (p.group.id, p.auditorium.id, p.cell, int(p.weekday))
            for p in self._last_result.placed
        ]
        if not assignments:
            if not silent:
                QMessageBox.warning(self, "Ошибка", "Нечего записывать: ни одна группа не размещена.")
            return (None, None)

        try:
            added, conflicts = self.db.save_schedule(
                teacher_id=ctx["teacher_id"],
                subject_id=ctx["subject_id"],
                kind=ctx["kind"],
                assignments=assignments,
            )
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Ошибка записи в расписание", str(e))
            return (None, None, None)

        total = len(assignments)
        conflict_msg = ""
        if conflicts:
            shown = "\n".join(
                f"• {c['group_name']} ({c['aud_name']}, пара {c['pair_number']}, "
                f"{WEEKDAYS[c['weekday']]}) — занято: {c['busy_by']}"
                for c in conflicts[:5]
            )
            extra = f"\n…и ещё {len(conflicts) - 5}" if len(conflicts) > 5 else ""
            conflict_msg = (
                f"\n\nНе записано из-за накладок ({len(conflicts)}): "
                f"в это время у преподавателя уже стоит другое занятие.\n"
                f"{shown}{extra}\n"
                f"Смените день на вкладке «6. Расписание» или удалите лишнее."
            )
        if not silent:
            if added == 0 and not conflicts:
                QMessageBox.information(
                    self, "Готово",
                    "Все эти занятия уже есть в расписании — ничего не добавлено.\n"
                    "Дубликаты пропущены автоматически."
                )
            elif added == 0:
                QMessageBox.warning(
                    self, "Ничего не записано",
                    "Все занятия отклонены из-за накладок:"
                    f"{conflict_msg}\n\n"
                    f"Преподаватель: «{self.teacher_combo.currentText()}»."
                )
            else:
                QMessageBox.information(
                    self, "Готово",
                    f"Добавлено занятий в расписание: {added}\n"
                    f"(пропущено дублей: {total - added - len(conflicts)})"
                    f"{conflict_msg}\n\n"
                    f"Преподаватель: «{self.teacher_combo.currentText()}»\n"
                    f"Использовано ячеек: {self._last_result.cells_used}\n\n"
                    f"Смотрите вкладку «6. Расписание»."
                )
            self.on_schedule_teacher_changed()

        return (added, total, conflicts)

    def distribute_and_write(self):

        # 1. Распределяем (без всплывающего окна)
        ok = self.distribute(silent=True)
        if not ok:
            return   # distribute() сам показал ошибку

        # 2. Пишем в расписание (без всплывающего окна)
        added, total, conflicts = self.write_to_schedule(silent=True)
        conflicts = conflicts or []

        # 3. Одно итоговое сообщение
        ctx = self._last_context or {}
        teacher_name = self.teacher_combo.currentText() if ctx.get("teacher_id") else "—"
        if added is None:
            # не удалось записать — сообщение уже было показано
            return

        conflict_msg = (
            f"\nОтклонено из-за накладок: {len(conflicts)} "
            f"(в это время уже стоит другое занятие)."
            if conflicts else ""
        )
        if added == 0 and not conflicts:
            QMessageBox.information(
                self, "Готово",
                f"Распределение выполнено.\n"
                f"Новых занятий в расписании нет — все уже были записаны (дубликаты пропущены).\n\n"
                f"Преподаватель: «{teacher_name}»\n"
                f"Использовано ячеек: {self._last_result.cells_used}"
            )
        else:
            QMessageBox.information(
                self, "Готово",
                f"Распределение выполнено и записано в расписание.\n\n"
                f"Добавлено занятий: {added}\n"
                f"Пропущено дублей: {total - added - len(conflicts)}"
                f"{conflict_msg}\n"
                f"Преподаватель: «{teacher_name}»\n"
                f"Использовано ячеек: {self._last_result.cells_used}"
            )

        self.on_schedule_teacher_changed()


    #РАСПИСАНИЕ

    def _build_schedule_tab(self):
        v = QVBoxLayout()
        self.tab_schedule.setLayout(v)

        top = QHBoxLayout()
        top.addWidget(QLabel("Преподаватель:"))
        self.schedule_teacher_combo = QComboBox()
        self.schedule_teacher_combo.currentIndexChanged.connect(self.on_schedule_teacher_changed)
        top.addWidget(self.schedule_teacher_combo, 1)
        v.addLayout(top)

        btns = QHBoxLayout()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.on_schedule_teacher_changed)
        btns.addWidget(refresh_btn)

        del_btn = QPushButton("🗑 Удалить выбранные занятия")
        del_btn.clicked.connect(self.delete_selected_schedule_rows)
        btns.addWidget(del_btn)

        clear_btn = QPushButton("Очистить всё расписание")
        clear_btn.clicked.connect(self.clear_current_teacher_schedule)
        btns.addWidget(clear_btn)

        to_table_btn = QPushButton("➡ В таблицу (7)")
        to_table_btn.setStyleSheet(
            "QPushButton { font-weight: bold; background-color: #2e7d32; }"
            "QPushButton:hover { background-color: #388e3c; }"
        )
        to_table_btn.clicked.connect(self.transfer_to_timetable)
        btns.addWidget(to_table_btn)

        btns.addStretch()
        v.addLayout(btns)

        v.addWidget(QLabel("Расписание"))
        self.schedule_table = QTableWidget(0, 6)
        self.schedule_table.setHorizontalHeaderLabels(
            ["Предмет", "Тип", "Ячейка", "Группа", "Аудитория", "День"]
        )
        hh = self.schedule_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.schedule_table.setColumnWidth(1, 100)
        self.schedule_table.setColumnWidth(2, 90)
        self.schedule_table.setColumnWidth(5, 90)
        self.schedule_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.schedule_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.schedule_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.schedule_table.setWordWrap(True)
        self.schedule_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        v.addWidget(self.schedule_table)

    def reload_schedule_teachers(self):
        if not hasattr(self, "schedule_teacher_combo"):
            return
        with signals_blocked(self.schedule_teacher_combo):
            current = self.schedule_teacher_combo.currentData()
            self.schedule_teacher_combo.clear()
            for t in self.db.get_teachers():
                self.schedule_teacher_combo.addItem(str(t["name"]), int(t["id"]))
            if current is not None:
                idx = self.schedule_teacher_combo.findData(current)
                if idx >= 0:
                    self.schedule_teacher_combo.setCurrentIndex(idx)
        self.on_schedule_teacher_changed()
        # Синхронизируем список преподавателей на вкладке 7
        if hasattr(self, "tab_calendar"):
            try:
                self.tab_calendar.reload_teachers()
            except Exception:
                pass

    def on_schedule_teacher_changed(self):
        tid = self.schedule_teacher_combo.currentData()
        with signals_blocked(self.schedule_table):
            self.schedule_table.clearSpans()
            self.schedule_table.setRowCount(0)
            if tid is None:
                return

            rows = self.db.get_teacher_schedule(int(tid))
            if not rows:
                return

            # ---- 1. Разбиваем на блоки: граница = смена (subject_id, kind) ----
            blocks: list[list[dict]] = []
            current: list[dict] = []
            prev_key: tuple | None = None
            for r in rows:
                key = (r["subject_id"], r["kind"])
                if prev_key is not None and key != prev_key:
                    blocks.append(current)
                    current = []
                current.append(r)
                prev_key = key
            if current:
                blocks.append(current)

            sep_rows: list[int] = []

            # ---- 2. Рисуем блоки с пустыми строками между ними ----
            for bi, block in enumerate(blocks):
                if bi > 0:
                    sep = self.schedule_table.rowCount()
                    self.schedule_table.insertRow(sep)
                    for c in range(self.schedule_table.columnCount()):
                        item = QTableWidgetItem("")
                        item.setFlags(Qt.ItemFlag.NoItemFlags)
                        self.schedule_table.setItem(sep, c, item)
                    sep_rows.append(sep)

                # Внутри блока — группировка по (subject, kind, cell, aud, weekday)
                grouped: dict[tuple, list[dict]] = {}
                for r in block:
                    try:
                        w = int(r.get("weekday", 0) or 0)
                    except (TypeError, ValueError):
                        w = 0
                    if w not in (0, 1, 2, 3, 4):
                        w = 0
                    k = (
                        r["subject_name"] or "—",
                        r["kind"],
                        r["pair_number"],
                        r["aud_name"],
                        w,
                    )
                    grouped.setdefault(k, []).append(r)

                ordered = sorted(
                    grouped.items(),
                    key=lambda kv: (kv[0][4], kv[0][2], kv[0][3]),  # по дню, ячейке, аудитории
                )

                for (subject, kind, cell, aud_name, weekday), items in ordered:
                    items_sorted = sorted(items, key=lambda it: it["group_name"])
                    groups_str = ", ".join(
                        f"{it['group_name']} ({it['students']} чел.)"
                        for it in items_sorted
                    )

                    r = self.schedule_table.rowCount()
                    self.schedule_table.insertRow(r)

                    item_subj = QTableWidgetItem(str(subject))
                    item_kind = QTableWidgetItem(KIND_LABELS.get(kind, kind))
                    item_cell = QTableWidgetItem(f"Ячейка {cell}")
                    item_grp = QTableWidgetItem(groups_str)
                    ids = [int(it["id"]) for it in items_sorted]
                    item_grp.setData(Qt.ItemDataRole.UserRole, ids)
                    item_aud = QTableWidgetItem(str(aud_name))

                    self.schedule_table.setItem(r, 0, item_subj)
                    self.schedule_table.setItem(r, 1, item_kind)
                    self.schedule_table.setItem(r, 2, item_cell)
                    self.schedule_table.setItem(r, 3, item_grp)
                    self.schedule_table.setItem(r, 4, item_aud)

                    day_combo = QComboBox()
                    for i, dname in enumerate(WEEKDAYS):
                        day_combo.addItem(dname, i)
                    idx = day_combo.findData(int(weekday))
                    if idx >= 0:
                        day_combo.setCurrentIndex(idx)
                    day_combo.currentIndexChanged.connect(
                        lambda _i, _ids=list(ids), _c=day_combo: self._on_schedule_day_changed(
                            _ids, _c.currentData()
                        )
                    )
                    self.schedule_table.setCellWidget(r, 5, day_combo)

            # ---- 3. Подгоняем высоту строк ----
            self.schedule_table.resizeRowsToContents()
            for r in range(self.schedule_table.rowCount()):
                if r in sep_rows:
                    self.schedule_table.setRowHeight(r, 12)
                else:
                    cur = self.schedule_table.rowHeight(r)
                    self.schedule_table.setRowHeight(r, max(cur, 34))

    def _on_schedule_day_changed(self, ids: list[int], weekday):
        if weekday is None:
            return
        try:
            self.db.update_schedule_weekday([int(i) for i in ids], int(weekday))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            self.on_schedule_teacher_changed()
            return
        # Живьём обновляем 7 вкладку, если там выбран тот же преподаватель
        try:
            tid = self.schedule_teacher_combo.currentData()
            if tid is not None and hasattr(self, "tab_calendar"):
                if self.tab_calendar.current_teacher_id() == int(tid):
                    self.tab_calendar.render()
        except Exception:
            pass

    def transfer_to_timetable(self):
        """Кнопка на вкладке 6: показать данные текущего преподавателя на вкладке 7."""
        tid = self.schedule_teacher_combo.currentData()
        if tid is None:
            QMessageBox.warning(self, "Ошибка", "Выберите преподавателя.")
            return
        try:
            self.tab_calendar.reload_teachers(keep_id=int(tid))
            self.tab_calendar.set_teacher(int(tid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        self.tabs.setCurrentWidget(self.tab_calendar)

    def delete_selected_schedule_rows(self):
        ids: set[int] = set()
        for rng in self.schedule_table.selectedRanges():
            for r in range(rng.topRow(), rng.bottomRow() + 1):
                item = self.schedule_table.item(r, 3)
                if item is None:
                    continue
                stored = item.data(Qt.ItemDataRole.UserRole)
                if not stored:
                    continue
                if isinstance(stored, (list, tuple)):
                    ids.update(int(x) for x in stored)
                else:
                    ids.add(int(stored))
        if not ids:
            QMessageBox.warning(
                self, "Ошибка",
                "Не выбрано ни одной строки расписания.\n"
                "Можно выделить несколько строк, зажав Ctrl или Shift."
            )
            return
        if QMessageBox.question(
            self, "Удаление",
            f"Удалить выбранные занятия ({len(ids)} шт.)?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_schedule_rows(sorted(ids))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.on_schedule_teacher_changed()


    def clear_current_teacher_schedule(self):
        tid = self.schedule_teacher_combo.currentData()
        if tid is None:
            QMessageBox.warning(self, "Ошибка", "Выберите преподавателя.")
            return
        name = self.schedule_teacher_combo.currentText()
        if QMessageBox.question(
            self, "Очистка",
            f"Удалить всё расписание преподавателя «{name}»?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.clear_teacher_schedule(int(tid))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))
            return
        self.on_schedule_teacher_changed()


    # ЭКСПОРТ / ИМПОРТ EXCEL

    def _refresh_all_tabs(self):
        self.reload_groups()
        self.reload_auditoriums()
        self.reload_teachers()
        self.reload_subjects()
        self.reload_courses()
        self.reload_schedule_teachers()
        if hasattr(self, "tab_calendar"):
            try:
                self.tab_calendar.reload_teachers()
            except Exception:
                pass

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в Excel", "schedule_export.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            from excel_io import export_to_excel
            stats = export_to_excel(self.db, path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))
            return
        details = "\n".join(f"{k}: {v}" for k, v in stats.items())
        QMessageBox.information(self, "Экспорт готов", f"Файл сохранён:\n{path}\n\n{details}")

    def import_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт из Excel", "",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            from excel_io import import_from_excel
            result = import_from_excel(self.db, path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))
            return
        self._refresh_all_tabs()
        lines = []
        for k, v in result["added"].items():
            lines.append(f"{k}: добавлено {v}")
        for k, v in result["updated"].items():
            lines.append(f"{k}: обновлено {v}")
        report = "\n".join(lines) if lines else "Новых данных нет."
        errors = result["errors"]
        if errors:
            report += f"\n\nОшибок в строках: {len(errors)} (первые 10):\n" + "\n".join(errors[:10])
        QMessageBox.information(self, "Импорт завершён", report)

    # ЗАКРЫТИЕ

    def closeEvent(self, event):
        try:
            self.db.close()
        finally:
            super().closeEvent(event)