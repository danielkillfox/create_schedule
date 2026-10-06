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


class GroupSelectModal(tk.Toplevel):
    def __init__(self, master, day_date, groups, assigned_ids, on_save):
        super().__init__(master)
        self.title(f"Занятия на {day_date.strftime('%d.%m.%Y')}")
        self.resizable(False, False)
        self.on_save = on_save
        self.day_date = day_date
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
        self.subject_entry = ttk.Entry(self, width=32)
        self.subject_entry.pack(fill="x", padx=12)

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
        try:
            api_request(
                "POST",
                "/schedule",
                {
                    "date": self.day_date.isoformat(),
                    "group_ids": group_ids,
                    "subject": self.subject_entry.get().strip(),
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
        self.title("Студенты и группы")
        self.geometry("460x480")
        self.groups = []

        top = ttk.LabelFrame(self, text="Добавить группу")
        top.pack(fill="x", padx=10, pady=(10, 5))
        self.group_entry = ttk.Entry(top)
        self.group_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        ttk.Button(top, text="Добавить", command=self.add_group).pack(side="right", padx=8, pady=8)

        mid = ttk.LabelFrame(self, text="Добавить студента")
        mid.pack(fill="x", padx=10, pady=5)
        self.student_entry = ttk.Entry(mid)
        self.student_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        self.group_combo = ttk.Combobox(mid, state="readonly", width=18)
        self.group_combo.pack(side="left", pady=8)
        ttk.Button(mid, text="Добавить", command=self.add_student).pack(side="right", padx=8, pady=8)

        bottom = ttk.LabelFrame(self, text="Все студенты")
        bottom.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        columns = ("name", "group")
        self.tree = ttk.Treeview(bottom, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="Студент")
        self.tree.heading("group", text="Группа")
        self.tree.column("name", width=220)
        self.tree.column("group", width=160)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        scroll = ttk.Scrollbar(bottom, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y", pady=8)
        self.tree.configure(yscrollcommand=scroll.set)

        ttk.Button(self, text="Удалить выбранного", command=self.delete_student).pack(pady=(0, 10))

        self.tree.bind("<Double-1>", lambda event: self.delete_student())
        self.transient(master)
        self.reload()

    def reload(self):
        try:
            payload = api_request("GET", "/groups")
            self.groups = payload["groups"]
            students = api_request("GET", "/students")["students"]
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
        ttk.Button(header, text="Студенты", command=self.open_students).pack(side="right")
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
                    text = entry["group_name"]
                    if entry["subject"]:
                        text = f"{entry['group_name']}: {entry['subject']}"
                    label = tk.Label(
                        cell,
                        text=text,
                        anchor="w",
                        justify="left",
                        bg="#bbdefb" if not is_today else "#aed581",
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
        except RuntimeError as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self.root)
            return
        assigned = [
            entry["group_id"] for entry in self.schedule.get(day_date.isoformat(), [])
        ]
        GroupSelectModal(self.root, day_date, groups, assigned, self.render)


def main():
    server.start_background(port=PORT)
    root = tk.Tk()
    CalendarApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
