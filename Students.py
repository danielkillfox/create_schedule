# Students.py
# =====================================================================
# Простая база данных студентов (файл students.db рядом с программой).
# Простыми словами:
# - Это как Excel, только надёжнее: таблицы "Группы", "Студенты",
#   "Преподаватели", "Предметы", "Расписание".
# - Каждая функция ниже - это одно действие: "добавить", "получить", "удалить".
# - Все данные хранятся в файле students.db, ничего не потеряется после закрытия.
# Словарик:
#   conn   = "соединение" с файлом базы (открыли файл, чтобы читать/писать)
#   cursor = "курсор" - то, чем мы выполняем команды на языке SQL
#   SQL    = язык запросов к базе, например "SELECT * FROM groups" = "дай всё из групп"
# =====================================================================

import sqlite3  # встроенная библиотека Python для работы с базой SQLite (файл-база)
from pathlib import Path  # помогает найти файл students.db рядом с этим файлом

# Находим файл базы: он лежит в той же папке, где и этот Students.py
DB_PATH = Path(__file__).with_name("students.db")


def get_connection():
    # Открыть базу и настроить её.
    # row_factory = sqlite3.Row позволяет обращаться к данным по имени: row["name"].
    # PRAGMA foreign_keys = ON включает проверку связей (нельзя сослаться на несуществующую группу).
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    # Создать все таблицы, если их ещё нет. Вызывается при старте программы.
    # IF NOT EXISTS значит "если таблица уже есть - не трогай её, данные не удаляй".
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
                teacher_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
                subject TEXT NOT NULL DEFAULT '',
                UNIQUE (date, group_id, subject_id, teacher_id, subject),
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            );
            """
        )
        _migrate_schedule(conn)


def _migrate_schedule(conn):
    # "Переезд" старой базы на новую. Если у кого-то остался старый файл students.db
    # без колонок subject_id/teacher_id - мы аккуратно пересоздаём таблицу
    # и переносим старые данные, ничего не теряя.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(schedule)")}
    if "subject_id" in columns and "teacher_id" in columns:
        return  # уже новая версия, делать ничего не надо
    conn.execute("ALTER TABLE schedule RENAME TO schedule_legacy")
    conn.executescript(
        """
        CREATE TABLE schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            group_id INTEGER NOT NULL,
            subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
            teacher_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
            subject TEXT NOT NULL DEFAULT '',
            UNIQUE (date, group_id, subject_id, teacher_id, subject),
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
        );

        INSERT INTO schedule (id, date, group_id, subject)
        SELECT id, date, group_id, subject FROM schedule_legacy;

        DROP TABLE schedule_legacy;
        """
    )


def add_group(name):
    # Добавить новую группу. Пример: add_group("ИСП-101").
    # strip() убирает случайные пробелы по краям. Пустое имя запрещаем.
    name = name.strip()
    if not name:
        raise ValueError("Название группы не может быть пустым")
    with get_connection() as conn:
        cursor = conn.execute("INSERT INTO groups (name) VALUES (?)", (name,))
        return cursor.lastrowid  # возвращаем номер новой группы (id)


def get_groups():
    # Получить все группы + посчитать, сколько студентов в каждой.
    # Вложенный SELECT COUNT(*) - это "подсчитай студентов этой группы".
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT g.id, g.name,
                   (SELECT COUNT(*) FROM students s WHERE s.group_id = g.id) AS students_count
            FROM groups g
            ORDER BY g.name
            """
        ).fetchall()
        return [dict(row) for row in rows]


def delete_group(group_id):
    # Удалить группу. Все её студенты и расписание тоже удалятся сами
    # (это настроено через ON DELETE CASCADE - "удаляй как лавина").
    with get_connection() as conn:
        conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))


def add_student(name, group_id):
    # Добавить студента в группу. Сначала проверяем, что такая группа существует.
    name = name.strip()
    if not name:
        raise ValueError("Имя студента не может быть пустым")
    with get_connection() as conn:
        group = conn.execute("SELECT id FROM groups WHERE id = ?", (group_id,)).fetchone()
        if group is None:
            raise ValueError("Группа не найдена")
        cursor = conn.execute(
            "INSERT INTO students (name, group_id) VALUES (?, ?)",
            (name, group_id),
        )
        return cursor.lastrowid


def get_students(group_id=None):
    # Получить студентов. Если group_id указан - только этой группы, если нет - всех.
    # JOIN groups нужен, чтобы рядом с именем студента показать и название его группы.
    query = """
        SELECT s.id, s.name, s.group_id, g.name AS group_name
        FROM students s
        JOIN groups g ON g.id = s.group_id
    """
    params = ()
    if group_id is not None:
        query += " WHERE s.group_id = ?"
        params = (group_id,)
    query += " ORDER BY g.name, s.name"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def delete_student(student_id):
    # Удалить одного студента по его номеру.
    with get_connection() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))


def add_teacher(name):
    # Добавить преподавателя. Имена должны быть уникальными - двух одинаковых не даём создать.
    # sqlite3.IntegrityError - это ошибка базы "такое уже есть", мы превращаем её в понятную фразу.
    name = name.strip()
    if not name:
        raise ValueError("Имя преподавателя не может быть пустым")
    with get_connection() as conn:
        try:
            cursor = conn.execute("INSERT INTO teachers (name) VALUES (?)", (name,))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Такой преподаватель уже есть") from exc
        return cursor.lastrowid


def get_teachers():
    # Все преподаватели + сколько занятий у каждого в расписании (чтобы видеть нагрузку).
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.name,
                   (SELECT COUNT(*) FROM schedule sc WHERE sc.teacher_id = t.id) AS lessons_count
            FROM teachers t
            ORDER BY t.name
            """
        ).fetchall()
        return [dict(row) for row in rows]


def delete_teacher(teacher_id):
    # Удалить преподавателя. Его занятия в расписании не пропадут, а станут "без преподавателя"
    # (это настроено через ON DELETE SET NULL).
    with get_connection() as conn:
        conn.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))


def add_subject(name):
    # Добавить предмет (например, "Математика"). Дубликаты запрещены.
    name = name.strip()
    if not name:
        raise ValueError("Название предмета не может быть пустым")
    with get_connection() as conn:
        try:
            cursor = conn.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Такой предмет уже есть") from exc
        return cursor.lastrowid


def get_subjects():
    # Все предметы + сколько занятий по каждому уже запланировано.
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.name,
                   (SELECT COUNT(*) FROM schedule sc WHERE sc.subject_id = s.id) AS lessons_count
            FROM subjects s
            ORDER BY s.name
            """
        ).fetchall()
        return [dict(row) for row in rows]


def delete_subject(subject_id):
    # Удалить предмет.
    with get_connection() as conn:
        conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))


def set_schedule(date, group_ids, subject="", subject_id=None, teacher_id=None):
    # Записать расписание на один день (дата вида "2026-10-12").
    # Логика: сначала стираем всё, что было на этот день, потом записываем заново.
    # INSERT OR IGNORE значит "если такая строчка уже есть - не ругайся, просто пропусти".
    with get_connection() as conn:
        conn.execute("DELETE FROM schedule WHERE date = ?", (date,))
        for group_id in group_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO schedule
                    (date, group_id, subject, subject_id, teacher_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, group_id, subject, subject_id, teacher_id),
            )


def get_schedule(year, month):
    # Получить расписание за месяц. Пример: get_schedule(2026, 10) = "весь октябрь 2026".
    # Мы ищем даты, которые начинаются как "2026-10-..." (знак % = "дальше что угодно").
    # COALESCE(x, '') значит "если пусто - покажи пустую строку, а не ошибку".
    prefix = f"{year:04d}-{month:02d}-%"
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT sc.id, sc.date, sc.group_id, sc.subject_id, sc.teacher_id,
                   COALESCE(sc.subject, '') AS subject,
                   COALESCE(su.name, '') AS subject_name,
                   g.name AS group_name,
                   COALESCE(t.name, '') AS teacher_name
            FROM schedule sc
            JOIN groups g ON g.id = sc.group_id
            LEFT JOIN subjects su ON su.id = sc.subject_id
            LEFT JOIN teachers t ON t.id = sc.teacher_id
            WHERE sc.date LIKE ?
            ORDER BY sc.date, g.name
            """,
            (prefix,),
        ).fetchall()
        return [dict(row) for row in rows]


def delete_schedule_entry(entry_id):
    # Удалить одну строчку расписания (одно занятие одной группы).
    with get_connection() as conn:
        conn.execute("DELETE FROM schedule WHERE id = ?", (entry_id,))


init_db()  # при подключении файла сразу создаём таблицы, чтобы всё было готово
