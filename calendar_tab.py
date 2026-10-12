# calendar_tab.py
"""Вкладка 7: сетка пар 6x5 (слева 1-6, сверху Пн-Пт).

Простыми словами:
- Это красивый календарь как в школе: строки = пары (1-я ... 6-я),
  столбцы = дни недели (Пн ... Пт).
- Данные берутся из вкладки 6 (таблица schedule) и фильтруются
  по преподавателю — так же, как на вкладке 6.
- День недели хранится в schedule.weekday (0=Пн..4=Пт),
  пара — в schedule.pair_number (1..6).
- Если в одну клетку попало два РАЗНЫХ занятия - клетка станет красной
  (накладка). Нажимаешь на неё - видишь подробности.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

import lang  # переводы интерфейса (tr = текст на текущем языке)
from lang import tr

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт"]  # дни недели по порядку (0=Пн ... 4=Пт). Русские названия оставлены для совместимости, на экране используются lang.weekday_names()
PAIRS = [1, 2, 3, 4, 5, 6]  # номера пар (уроков) в день

KIND_SHORT = {"lecture": "Л", "practice": "П"}  # короткая пометка в клетке: Л=лекция, П=практика

# Три вида раскраски клетки: пустая (серая), занятая (зеленоватая), красная (накладка/конфликт).
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
CELL_CONFLICT = """
    QFrame { background-color: #4a2b2b; border: 2px solid #e53935;
             border-radius: 4px; }
    QFrame:hover { border: 2px solid #ff7961; }
"""


class SlotCell(QFrame):
    """Одна ячейка сетки (пара x день недели), только для показа.

    Это один квадратик календаря. Внутри - текст (что за занятие).
    По клику мышки сообщает наружу: "нажали на пару X в день Y".
    """

    clicked = pyqtSignal(int, int)  # сигнал "кликнули": (номер пары, номер дня 0-4)

    def __init__(self, pair: int, day_col: int, parent=None):
        # Создать пустую клетку для пары pair и дня day_col.
        super().__init__(parent)
        self.pair = pair  # запоминаем, за какую пару отвечает клетка
        self.day_col = day_col  # и за какой день (0=Пн)
        self.setCursor(Qt.CursorShape.PointingHandCursor)  # курсор-рука при наведении
        self.setStyleSheet(CELL_NORMAL)  # пока пустая - серая
        self.setMinimumHeight(84)
        self.setMinimumWidth(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        self.text_label = QLabel("")  # текст внутри клетки (предмет, группы, зал)
        self.text_label.setWordWrap(True)  # длинные строки переносим, а не обрезаем
        self.text_label.setStyleSheet(
            "background: transparent; color: #e6e6e6; font-size: 12px;"
        )
        # Клики должны доходить до самой клетки, а не застревать в тексте:
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.text_label)
        layout.addStretch(1)

    def set_text(self, text: str, conflict: bool = False):
        # Показать текст в клетке и перекрасить её.
        # conflict=True = красная (два разных занятия в одно время!).
        self.text_label.setText(text)
        if conflict:
            self.setStyleSheet(CELL_CONFLICT)
        else:
            self.setStyleSheet(CELL_FILLED if text else CELL_NORMAL)

    def mousePressEvent(self, event):
        # Человек нажал мышкой на клетку: кричим "кликнули!" и передаём её координаты.
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.pair, self.day_col)
        super().mousePressEvent(event)


class CalendarTab(QWidget):
    """Вкладка-сетка: строки 1-6, столбцы Пн-Пт, фильтр по преподавателю.

    Сверху - выбор преподавателя и кнопка "Обновить".
    Ниже - сама сетка 6x5. При открытии вкладки она перерисовывается сама.
    """

    def __init__(self, db, parent=None):
        # Запоминаем базу данных, готовим пустые словари для клеток и подсказок,
        # строим внешний вид и загружаем список преподавателей.
        super().__init__(parent)
        self.db = db
        self.cells: dict[tuple[int, int], SlotCell] = {}  # (пара, день) -> клетка на экране
        self._details: dict[tuple[int, int], str] = {}  # (пара, день) -> полный текст для всплывающего окна
        self._build_ui()
        self.reload_teachers()

    def _build_ui(self):
        # Построить внешний вид: верхняя строка (преподаватель + обновить) и сетка.
        # Все подписи берём из переводов tr(), а ссылки на них запоминаем,
        # чтобы retranslate_ui() мог поменять язык без перезапуска.
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.teacher_label = QLabel(tr("cal_teacher"))
        top.addWidget(self.teacher_label)
        self.teacher_combo = QComboBox()
        self.teacher_combo.currentIndexChanged.connect(self.render)
        top.addWidget(self.teacher_combo, 1)
        self.refresh_btn = QPushButton(tr("btn_refresh"))
        self.refresh_btn.clicked.connect(self.render)
        top.addWidget(self.refresh_btn)
        layout.addLayout(top)

        grid = QGridLayout()
        grid.setSpacing(2)

        grid.addWidget(QLabel(""), 0, 0)

        self.day_labels: list[QLabel] = []  # заголовки дней недели (Пн..Пт), чтобы переименовывать их
        for col, name in enumerate(lang.weekday_names()):
            lbl = QLabel(name, alignment=Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-weight: bold;")
            grid.addWidget(lbl, 0, col + 1)
            self.day_labels.append(lbl)

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

    def retranslate_ui(self):
        # Переключить все подписи вкладки на текущий язык (вызывается из настроек).
        # Дни недели берём из переводов, затем перерисовываем сетку.
        self.teacher_label.setText(tr("cal_teacher"))
        self.refresh_btn.setText(tr("btn_refresh"))
        for col, name in enumerate(lang.weekday_names()):
            if col < len(self.day_labels):
                self.day_labels[col].setText(name)
        self.render()

    # ---- преподаватели (как на вкладке 6) ----

    def reload_teachers(self, keep_id: int | None = None):
        """Перечитать список преподавателей, по возможности сохранив выбор.

        keep_id: если знаем, кого надо выбрать после обновления - выбираем его.
        Сигналы блокируем, чтобы смена списка не вызывала лишних перерисовок.
        """
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
        """Выбрать преподавателя (используется кнопкой с вкладки 6 "В таблицу").

        Если такого препода нет в списке - обновляем список и пробуем снова.
        """
        if teacher_id is None:
            return
        idx = self.teacher_combo.findData(int(teacher_id))
        if idx >= 0:
            self.teacher_combo.setCurrentIndex(idx)
        else:
            self.reload_teachers(keep_id=int(teacher_id))
        self.render()

    def current_teacher_id(self) -> int | None:
        # Номер выбранного сейчас преподавателя (или None, если никого нет).
        return self.teacher_combo.currentData()

    # ---- отрисовка из schedule (главная магия вкладки) ----

    def render(self):
        # Перерисовать всю сетку для выбранного преподавателя:
        # 1) очистить все клетки, 2) взять его занятия из базы,
        # 3) разложить их по клеткам (день, пара), 4) подсветить накладки красным.
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
                # День недели показываем на текущем языке (перерисовка подхватит смену языка).
                day_name = lang.weekday_names()[w]
                full_lines.append(
                    f"{subj}{tag} — {groups} — {aud} "
                    f"(пара {p}, {day_name})"
                )
            cell.set_text("\n— — —\n".join(short_lines), conflict=len(inner) > 1)
            details = "\n".join(full_lines)
            if len(inner) > 1:
                details = (
                    f"⚠ НАКЛАДКА: {len(inner)} разных занятия "
                    f"в одно время (пара {p}, {lang.weekday_names()[w]}).\n"
                    f"Оставьте одно: лишнее удалите или перенесите день "
                    f"на вкладке «6. Расписание».\n\n{details}"
                )
            self._details[(p, w)] = details

    def show_details(self, pair: int, day_col: int):
        # Человек кликнул на клетку: показываем всплывающее окно с полным описанием.
        # Если клетка пустая - ничего не показываем, чтобы не надоедать.
        text = self._details.get((pair, day_col), "")
        if not text:
            return
        QMessageBox.information(
            self, f"Пара {pair}, {lang.weekday_names()[day_col]}", text
        )

    def showEvent(self, event):
        # Этот метод вызывается сам, когда вкладку открывают.
        # Обновляем сетку, чтобы всегда видеть свежие данные.
        super().showEvent(event)
        self.render()
