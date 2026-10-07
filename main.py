import calendar
import json
import urllib.error
import urllib.request
from datetime import date

import tkinter as tk
from tkinter import messagebox, ttk

import server

API = "http://127.0.0.1:5000/api"
PORT = 5000

MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def api_request(method, path, data=None):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request_obj = urllib.request.Request(
        API + path, data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8") or "{}")
        raise RuntimeError(payload.get("error", str(exc))) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Сервер недоступен") from exc


NO_VALUE = "— не выбрано —"
SUBJECT_COLORS = [
    "#bbdefb", "#c8e6c9", "#fff9c4", "#f8bbd0",
    "#e1bee7", "#ffccbc", "#b2ebf2", "#ffe0b2",
]


def _initial_index(items, item_id):
    if item_id is None:
        return 0
    for index, item in enumerate(items, start=1):
        if item["id"] == item_id:
            return index
    return 0


def _entry_color(subject_id):
    if subject_id is None:
        return "#eceff1"
    return SUBJECT_COLORS[(subject_id - 1) % len(SUBJECT_COLORS)]


class GroupSelectModal(tk.Toplevel):
    def __init__(self, master, day_date, groups, assigned_ids,
                 subjects, teachers, initial, on_save):
        super().__init__(master)
        self.title(f"Занятия на {day_date.strftime('%d.%m.%Y')}")
        self.resizable(False, False)
        self.on_save = on_save
        self.day_date = day_date
        self.subjects = subjects
        self.teachers = teachers
        self.vars = {}

        ttk.Label(self, text="Выберите группы:").pack(anchor="w", padx=12, pady=(12, 4))

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=12)

        if not groups:
            ttk.Label(frame, text="Нет групп. Сначала добавьте их.").pack(anchor="w")
        for group in groups:
            var = tk.BooleanVar(value=group["id"] in assigned_ids)
            self.vars[group["id"]] = var
            ttk.Checkbutton(
                frame,
                text=f"{group['name']} ({group['students_count']} студ.)",
                variable=var,
            ).pack(anchor="w", pady=2)

        ttk.Label(self, text="Предмет:").pack(anchor="w", padx=12, pady=(10, 2))
        self.subject_combo = ttk.Combobox(self, state="readonly", width=34)
        self.subject_combo["values"] = [NO_VALUE] + [s["name"] for s in subjects]
        self.subject_combo.current(_initial_index(subjects, initial.get("subject_id")))
        self.subject_combo.pack(fill="x", padx=12)

        ttk.Label(self, text="Преподаватель:").pack(anchor="w", padx=12, pady=(10, 2))
        self.teacher_combo = ttk.Combobox(self, state="readonly", width=34)
        self.teacher_combo["values"] = [NO_VALUE] + [t["name"] for t in teachers]
        self.teacher_combo.current(_initial_index(teachers, initial.get("teacher_id")))
        self.teacher_combo.pack(fill="x", padx=12)

        if not subjects:
            ttk.Label(self, text="Нет предметов — добавьте их в справочнике",
                      foreground="#b71c1c").pack(anchor="w", padx=12, pady=(6, 0))
        if not teachers:
            ttk.Label(self, text="Нет преподавателей — добавьте их в справочнике",
                      foreground="#b71c1c").pack(anchor="w", padx=12, pady=(4, 0))

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", padx=12, pady=12)
        ttk.Button(buttons, text="Сохранить", command=self.save).pack(side="right")
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(side="right", padx=6)

        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda event: self.destroy())
        self.focus_set()

    def save(self):
        group_ids = [gid for gid, var in self.vars.items() if var.get()]
        subject_index = self.subject_combo.current()
        teacher_index = self.teacher_combo.current()
        subject_id = (
            self.subjects[subject_index - 1]["id"] if subject_index > 0 else None
        )
        teacher_id = (
            self.teachers[teacher_index - 1]["id"] if teacher_index > 0 else None
        )
        try:
            api_request(
                "POST",
                "/schedule",
                {
                    "date": self.day_date.isoformat(),
                    "group_ids": group_ids,
                    "subject_id": subject_id,
                    "teacher_id": teacher_id,
                },
            )
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return
        self.on_save()
        self.destroy()


class StudentsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Справочники")
        self.geometry("520x540")
        self.groups = []
        self.subjects = []
        self.teachers = []

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.students_tab = ttk.Frame(notebook)
        self.subjects_tab = ttk.Frame(notebook)
        self.teachers_tab = ttk.Frame(notebook)
        notebook.add(self.students_tab, text="Студенты")
        notebook.add(self.subjects_tab, text="Предметы")
        notebook.add(self.teachers_tab, text="Преподаватели")

        self._build_students_tab()
        self._build_subjects_tab()
        self._build_teachers_tab()

        self.transient(master)
        self.reload()

    def _build_students_tab(self):
        top = ttk.LabelFrame(self.students_tab, text="Добавить группу")
        top.pack(fill="x", padx=8, pady=(8, 4))
        self.group_entry = ttk.Entry(top)
        self.group_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        ttk.Button(top, text="Добавить", command=self.add_group).pack(side="right", padx=8, pady=8)

        mid = ttk.LabelFrame(self.students_tab, text="Добавить студента")
        mid.pack(fill="x", padx=8, pady=4)
        self.student_entry = ttk.Entry(mid)
        self.student_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        self.group_combo = ttk.Combobox(mid, state="readonly", width=18)
        self.group_combo.pack(side="left", pady=8)
        ttk.Button(mid, text="Добавить", command=self.add_student).pack(side="right", padx=8, pady=8)

        bottom = ttk.LabelFrame(self.students_tab, text="Все студенты")
        bottom.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        columns = ("name", "group")
        self.tree = ttk.Treeview(bottom, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="Студент")
        self.tree.heading("group", text="Группа")
        self.tree.column("name", width=240)
        self.tree.column("group", width=170)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        scroll = ttk.Scrollbar(bottom, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y", pady=8)
        self.tree.configure(yscrollcommand=scroll.set)

        ttk.Button(self.students_tab, text="Удалить выбранного",
                   command=self.delete_student).pack(pady=(0, 8))
        self.tree.bind("<Double-1>", lambda event: self.delete_student())

    def _build_list_tab(self, tab, title, entries, add_command, delete_command,
                        entry_attr, list_attr):
        top = ttk.LabelFrame(tab, text=title)
        top.pack(fill="x", padx=8, pady=(8, 4))
        field = ttk.Entry(top)
        field.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        ttk.Button(top, text="Добавить", command=add_command).pack(side="right", padx=8, pady=8)
        setattr(self, entry_attr, field)

        bottom = ttk.LabelFrame(tab, text=entries)
        bottom.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        listbox = tk.Listbox(bottom, font=("Segoe UI", 10))
        listbox.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        setattr(self, list_attr, listbox)

        scroll = ttk.Scrollbar(bottom, orient="vertical", command=listbox.yview)
        scroll.pack(side="right", fill="y", pady=8)
        listbox.configure(yscrollcommand=scroll.set)

        ttk.Button(tab, text="Удалить выбранное",
                   command=delete_command).pack(pady=(0, 8))

    def _build_subjects_tab(self):
        self._build_list_tab(
            self.subjects_tab, "Добавить предмет", "Все предметы",
            self.add_subject, self.delete_subject,
            "subject_entry", "subject_list",
        )

    def _build_teachers_tab(self):
        self._build_list_tab(
            self.teachers_tab, "Добавить преподавателя", "Все преподаватели",
            self.add_teacher, self.delete_teacher,
            "teacher_entry", "teacher_list",
        )

    def reload(self):
        try:
            self.groups = api_request("GET", "/groups")["groups"]
            students = api_request("GET", "/students")["students"]
            self.subjects = api_request("GET", "/subjects")["subjects"]
            self.teachers = api_request("GET", "/teachers")["teachers"]
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return

        names = [f"{g['name']} ({g['students_count']})" for g in self.groups]
        self.group_combo["values"] = names
        if self.groups and self.group_combo.current() == -1:
            self.group_combo.current(0)
        self.tree.delete(*self.tree.get_children())
        for student in students:
            self.tree.insert("", "end", iid=str(student["id"]),
                             values=(student["name"], student["group_name"]))

        self.subject_list.delete(0, "end")
        for subject in self.subjects:
            self.subject_list.insert(
                "end", f"{subject['name']} (занятий: {subject['lessons_count']})"
            )
        self.teacher_list.delete(0, "end")
        for teacher in self.teachers:
            self.teacher_list.insert(
                "end", f"{teacher['name']} (занятий: {teacher['lessons_count']})"
            )

    def add_group(self):
        name = self.group_entry.get().strip()
        if not name:
            return
        try:
            api_request("POST", "/groups", {"name": name})
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return
        self.group_entry.delete(0, "end")
        self.reload()

    def add_student(self):
        name = self.student_entry.get().strip()
        index = self.group_combo.current()
        if not name or index < 0 or index >= len(self.groups):
            messagebox.showwarning("Внимание", "Введите имя и выберите группу", parent=self)
            return
        try:
            api_request("POST", "/students",
                        {"name": name, "group_id": self.groups[index]["id"]})
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return
        self.student_entry.delete(0, "end")
        self.reload()

    def delete_student(self):
        selection = self.tree.selection()
        if not selection:
            return
        try:
            api_request("DELETE", f"/students/{int(selection[0])}")
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return
        self.reload()

    def add_subject(self):
        name = self.subject_entry.get().strip()
        if not name:
            return
        try:
            api_request("POST", "/subjects", {"name": name})
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return
        self.subject_entry.delete(0, "end")
        self.reload()

    def delete_subject(self):
        selection = self.subject_list.curselection()
        if not selection or selection[0] >= len(self.subjects):
            return
        subject = self.subjects[selection[0]]
        try:
            api_request("DELETE", f"/subjects/{subject['id']}")
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return
        self.reload()

    def add_teacher(self):
        name = self.teacher_entry.get().strip()
        if not name:
            return
        try:
            api_request("POST", "/teachers", {"name": name})
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return
        self.teacher_entry.delete(0, "end")
        self.reload()

    def delete_teacher(self):
        selection = self.teacher_list.curselection()
        if not selection or selection[0] >= len(self.teachers):
            return
        teacher = self.teachers[selection[0]]
        try:
            api_request("DELETE", f"/teachers/{teacher['id']}")
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            return
        self.reload()


class CalendarApp:
    def __init__(self, root):
        self.root = root
        today = date.today()
        self.year = today.year
        self.month = today.month
        self.schedule = {}
        self.cells = {}

        root.title("Расписание занятий")
        root.geometry("980x660")
        root.minsize(860, 580)

        header = ttk.Frame(root)
        header.pack(fill="x", padx=10, pady=10)

        ttk.Button(header, text="‹", width=3, command=self.prev_month).pack(side="left")
        self.title_label = ttk.Label(header, text="", font=("Segoe UI", 14, "bold"))
        self.title_label.pack(side="left", padx=8)
        ttk.Button(header, text="›", width=3, command=self.next_month).pack(side="left")
        ttk.Button(header, text="Сегодня", command=self.go_today).pack(side="left", padx=12)
        ttk.Button(header, text="Справочники", command=self.open_students).pack(side="right")
        ttk.Button(header, text="Обновить", command=self.refresh).pack(side="right", padx=6)

        grid_frame = ttk.Frame(root)
        grid_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        grid_frame.columnconfigure(tuple(range(7)), weight=1)

        for col, name in enumerate(WEEKDAYS):
            ttk.Label(grid_frame, text=name, anchor="center",
                      font=("Segoe UI", 10, "bold")).grid(
                row=0, column=col, sticky="nsew", padx=1, pady=1
            )

        for row in range(1, 7):
            grid_frame.rowconfigure(row, weight=1)
            for col in range(7):
                cell = tk.Frame(
                    grid_frame,
                    relief="solid",
                    bd=1,
                    bg="#ffffff",
                    cursor="hand2",
                )
                cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                cell.bind("<Button-1>", lambda event, c=cell: self.on_cell_click(c))
                for child in cell.winfo_children():
                    child.bind("<Button-1>", lambda event, c=cell: self.on_cell_click(c))
                self.cells[(row, col)] = cell

        self.grid_frame = grid_frame
        self.render()

    def open_students(self):
        StudentsWindow(self.root)

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

    def load_schedule(self):
        try:
            payload = api_request("GET", f"/schedule?year={self.year}&month={self.month}")
        except RuntimeError:
            self.schedule = {}
            return
        self.schedule = {}
        for entry in payload["schedule"]:
            self.schedule.setdefault(entry["date"], []).append(entry)

    def refresh(self):
        self.render()

    def render(self):
        self.title_label.config(text=f"{MONTHS[self.month - 1]} {self.year}")
        self.load_schedule()

        for cell in self.cells.values():
            for child in cell.winfo_children():
                child.destroy()
            cell.configure(bg="#ffffff")

        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self.year, self.month)
        while len(weeks) < 6:
            weeks.append([])
        if len(weeks) > 6:
            weeks = weeks[:6]

        today = date.today()
        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                cell = self.cells[(row, col)]
                if day == 0:
                    cell.configure(bg="#f0f0f0")
                    continue
                day_date = date(self.year, self.month, day)
                is_today = day_date == today
                if is_today:
                    cell.configure(bg="#dcedc8")

                number = tk.Label(
                    cell,
                    text=str(day),
                    anchor="w",
                    bg=cell.cget("bg"),
                    font=("Segoe UI", 10, "bold" if is_today else "normal"),
                )
                number.pack(fill="x", padx=4, pady=(2, 0))
                number.bind("<Button-1>", lambda event, c=cell: self.on_cell_click(c))

                entries = self.schedule.get(day_date.isoformat(), [])
                for entry in entries:
                    parts = [entry["group_name"]]
                    subject = entry.get("subject_name") or entry.get("subject")
                    if subject:
                        parts.append(subject)
                    teacher = entry.get("teacher_name")
                    if teacher:
                        parts.append(teacher)
                    label = tk.Label(
                        cell,
                        text=" · ".join(parts),
                        anchor="w",
                        justify="left",
                        wraplength=120,
                        bg=_entry_color(entry.get("subject_id")),
                        font=("Segoe UI", 8),
                        padx=3,
                    )
                    label.pack(fill="x", padx=2, pady=1)
                    label.bind(
                        "<Button-1>",
                        lambda event, c=cell: self.on_cell_click(c),
                    )

    def on_cell_click(self, cell):
        position = None
        for key, value in self.cells.items():
            if value is cell:
                position = key
                break
        if position is None:
            return
        row, col = position
        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self.year, self.month)
        day = weeks[row - 1][col] if row - 1 < len(weeks) else 0
        if day == 0:
            return
        day_date = date(self.year, self.month, day)
        try:
            groups = api_request("GET", "/groups")["groups"]
            subjects = api_request("GET", "/subjects")["subjects"]
            teachers = api_request("GET", "/teachers")["teachers"]
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self.root)
            return
        day_entries = self.schedule.get(day_date.isoformat(), [])
        assigned = [entry["group_id"] for entry in day_entries]
        initial = {"subject_id": None, "teacher_id": None}
        if day_entries:
            initial["subject_id"] = day_entries[0].get("subject_id")
            initial["teacher_id"] = day_entries[0].get("teacher_id")
        GroupSelectModal(
            self.root, day_date, groups, assigned,
            subjects, teachers, initial, self.render,
        )


def main():
    server.start_background(port=PORT)
    root = tk.Tk()
    CalendarApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
