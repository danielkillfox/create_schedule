import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("students.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
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
    columns = {row[1] for row in conn.execute("PRAGMA table_info(schedule)")}
    if "subject_id" in columns and "teacher_id" in columns:
        return
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
    name = name.strip()
    if not name:
        raise ValueError("Название группы не может быть пустым")
    with get_connection() as conn:
        cursor = conn.execute("INSERT INTO groups (name) VALUES (?)", (name,))
        return cursor.lastrowid


def get_groups():
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
    with get_connection() as conn:
        conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))


def add_student(name, group_id):
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
    with get_connection() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))


def add_teacher(name):
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
    with get_connection() as conn:
        conn.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))


def add_subject(name):
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
    with get_connection() as conn:
        conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))


def set_schedule(date, group_ids, subject="", subject_id=None, teacher_id=None):
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
    with get_connection() as conn:
        conn.execute("DELETE FROM schedule WHERE id = ?", (entry_id,))


init_db()
