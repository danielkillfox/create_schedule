# server.py
# =====================================================================
# Это "мини-сайт" (сервер) для работы с базой студентов students.db.
# Простыми словами:
# - Программа запускает небольшой интернет-сервер на вашем компьютере.
# - Другие программы (или браузер) могут просить его:
#   "дай список групп", "добавь студента", "покажи расписание за месяц".
# - Общение идёт через адреса (как страницы сайта):
#   GET  /api/groups    - "дай список групп" (прочитать)
#   POST /api/groups    - "создай новую группу" (отправить данные)
#   DELETE /api/groups/1 - "удали группу с номером 1"
# - Ответ всегда в формате JSON: {"ok": True, ...} или {"ok": False, "error": "..."}.
# Запуск: python server.py  (потом открыть http://127.0.0.1:5000)
# =====================================================================

import json  # нужен, чтобы вручную разбирать текст как JSON
import threading  # нужен, чтобы запускать сервер "в фоне", не блокируя окно

import Students  # наш файл с базой данных (группы, студенты, расписание)
from flask import Flask, jsonify, request  # Flask - библиотека для создания сайтов/серверов

# Создаём само приложение-сервер. app - как "ресторан", а функции ниже - "официанты".
app = Flask(__name__)


def _payload():
    # Эта функция-помощник достаёт данные, которые прислал пользователь.
    # Данные могут прийти двумя способами, мы поддерживаем оба:
    # 1) как JSON (современный способ), 2) как просто текст.
    # Если ничего понять не удалось - возвращаем пустой словарь {}.
    if request.is_json:
        return request.get_json(silent=True) or {}
    if request.data:
        try:
            return json.loads(request.data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}
    return {}


def _error(message, status=400):
    # Помощник для ответа "что-то пошло не так".
    # Пример: {"ok": False, "error": "Не указана группа"}
    # status=400 означает "ошибка от пользователя" (а не поломка сервера).
    return jsonify({"ok": False, "error": message}), status


@app.get("/api/groups")
def groups_list():
    # Когда кто-то открывает адрес /api/groups, отдаём весь список групп.
    return jsonify({"ok": True, "groups": Students.get_groups()})


@app.post("/api/groups")
def groups_create():
    # Когда кто-то отправляет сюда {"name": "Группа-101"}, создаём новую группу.
    data = _payload()  # достаём присланное имя
    try:
        group_id = Students.add_group(data.get("name", ""))
    except ValueError as exc:
        return _error(str(exc))  # например, имя пустое - жалуемся в ответ
    return jsonify({"ok": True, "id": group_id}), 201  # 201 = "успешно создано"


@app.delete("/api/groups/<int:group_id>")
def groups_delete(group_id):
    # Удаление группы по номеру. Пример: DELETE /api/groups/5 удалит группу 5.
    Students.delete_group(group_id)
    return jsonify({"ok": True})


@app.get("/api/students")
def students_list():
    # Список студентов. Можно попросить всех, а можно одной группы: /api/students?group_id=2
    group_id = request.args.get("group_id", type=int)
    return jsonify({"ok": True, "students": Students.get_students(group_id)})


@app.post("/api/students")
def students_create():
    # Создание студента. Нужно прислать {"name": "Иван", "group_id": 2}.
    data = _payload()
    group_id = data.get("group_id")
    if not isinstance(group_id, int):
        return _error("Не указана группа")  # без группы не знаем, куда записать
    try:
        student_id = Students.add_student(data.get("name", ""), group_id)
    except ValueError as exc:
        return _error(str(exc))
    return jsonify({"ok": True, "id": student_id}), 201


@app.delete("/api/students/<int:student_id>")
def students_delete(student_id):
    # Удалить студента по его номеру.
    Students.delete_student(student_id)
    return jsonify({"ok": True})


@app.get("/api/teachers")
def teachers_list():
    # Просто отдать всех преподавателей.
    return jsonify({"ok": True, "teachers": Students.get_teachers()})


@app.post("/api/teachers")
def teachers_create():
    # Создать преподавателя по имени: {"name": "Петров"}
    data = _payload()
    try:
        teacher_id = Students.add_teacher(data.get("name", ""))
    except ValueError as exc:
        return _error(str(exc))
    return jsonify({"ok": True, "id": teacher_id}), 201


@app.delete("/api/teachers/<int:teacher_id>")
def teachers_delete(teacher_id):
    # Удалить преподавателя по номеру.
    Students.delete_teacher(teacher_id)
    return jsonify({"ok": True})


@app.get("/api/subjects")
def subjects_list():
    # Отдать все предметы (Математика, Физика...).
    return jsonify({"ok": True, "subjects": Students.get_subjects()})


@app.post("/api/subjects")
def subjects_create():
    # Создать предмет: {"name": "Математика"}
    data = _payload()
    try:
        subject_id = Students.add_subject(data.get("name", ""))
    except ValueError as exc:
        return _error(str(exc))
    return jsonify({"ok": True, "id": subject_id}), 201


@app.delete("/api/subjects/<int:subject_id>")
def subjects_delete(subject_id):
    # Удалить предмет по номеру.
    Students.delete_subject(subject_id)
    return jsonify({"ok": True})


@app.get("/api/schedule")
def schedule_list():
    # Расписание за конкретный месяц. Пример: /api/schedule?year=2026&month=10
    # Без года и месяца не поймём, что показать, поэтому требуем их.
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    if not year or not month:
        return _error("Нужны параметры year и month")
    return jsonify({"ok": True, "schedule": Students.get_schedule(year, month)})


@app.post("/api/schedule")
def schedule_set():
    # Записать, какие группы в какой день учатся.
    # Нужно прислать: {"date": "2026-10-12", "group_ids": [1, 2], ...}
    data = _payload()
    date = data.get("date")
    group_ids = data.get("group_ids")
    if not date or not isinstance(group_ids, list):
        return _error("Нужны date и group_ids")
    subject_id = data.get("subject_id")
    teacher_id = data.get("teacher_id")
    # Проверяем, что номера - это правда числа, а не текст.
    if subject_id is not None and not isinstance(subject_id, int):
        return _error("subject_id должен быть числом")
    if teacher_id is not None and not isinstance(teacher_id, int):
        return _error("teacher_id должен быть числом")
    Students.set_schedule(
        date,
        group_ids,
        data.get("subject", ""),
        subject_id,
        teacher_id,
    )
    return jsonify({"ok": True})


@app.delete("/api/schedule/<int:entry_id>")
def schedule_delete(entry_id):
    # Удалить одну строчку расписания по её номеру.
    Students.delete_schedule_entry(entry_id)
    return jsonify({"ok": True})


def run(host="127.0.0.1", port=5000):
    # Обычный запуск сервера: сначала создаём таблицы в базе, потом включаем сайт.
    # host="127.0.0.1" значит "только для этого компьютера" (безопасно).
    Students.init_db()
    app.run(host=host, port=port, threaded=True)


def start_background(host="127.0.0.1", port=5000):
    # Запуск "в фоне": сервер работает параллельно и не мешает окну программы.
    # daemon=True значит "выключится сам, когда закроется основная программа".
    thread = threading.Thread(target=run, kwargs={"host": host, "port": port}, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    run()  # если запустили python server.py напрямую - просто включаем сервер
