import json
import threading

import Students
from flask import Flask, jsonify, request

app = Flask(__name__)


def _payload():
    if request.is_json:
        return request.get_json(silent=True) or {}
    if request.data:
        try:
            return json.loads(request.data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}
    return {}


def _error(message, status=400):
    return jsonify({"ok": False, "error": message}), status


@app.get("/api/groups")
def groups_list():
    return jsonify({"ok": True, "groups": Students.get_groups()})


@app.post("/api/groups")
def groups_create():
    data = _payload()
    try:
        group_id = Students.add_group(data.get("name", ""))
    except ValueError as exc:
        return _error(str(exc))
    return jsonify({"ok": True, "id": group_id}), 201


@app.delete("/api/groups/<int:group_id>")
def groups_delete(group_id):
    Students.delete_group(group_id)
    return jsonify({"ok": True})


@app.get("/api/students")
def students_list():
    group_id = request.args.get("group_id", type=int)
    return jsonify({"ok": True, "students": Students.get_students(group_id)})


@app.post("/api/students")
def students_create():
    data = _payload()
    group_id = data.get("group_id")
    if not isinstance(group_id, int):
        return _error("Не указана группа")
    try:
        student_id = Students.add_student(data.get("name", ""), group_id)
    except ValueError as exc:
        return _error(str(exc))
    return jsonify({"ok": True, "id": student_id}), 201


@app.delete("/api/students/<int:student_id>")
def students_delete(student_id):
    Students.delete_student(student_id)
    return jsonify({"ok": True})


@app.get("/api/schedule")
def schedule_list():
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    if not year or not month:
        return _error("Нужны параметры year и month")
    return jsonify({"ok": True, "schedule": Students.get_schedule(year, month)})


@app.post("/api/schedule")
def schedule_set():
    data = _payload()
    date = data.get("date")
    group_ids = data.get("group_ids")
    if not date or not isinstance(group_ids, list):
        return _error("Нужны date и group_ids")
    Students.set_schedule(date, group_ids, data.get("subject", ""))
    return jsonify({"ok": True})


@app.delete("/api/schedule/<int:entry_id>")
def schedule_delete(entry_id):
    Students.delete_schedule_entry(entry_id)
    return jsonify({"ok": True})


def run(host="127.0.0.1", port=5000):
    Students.init_db()
    app.run(host=host, port=port, threaded=True)


def start_background(host="127.0.0.1", port=5000):
    thread = threading.Thread(target=run, kwargs={"host": host, "port": port}, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    run()
