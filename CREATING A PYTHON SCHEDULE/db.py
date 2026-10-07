# db.py
import sqlite3


class DB:
    def __init__(self, path="schedule.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.c = self.conn.cursor()
        self._init_schema()

    # ==================== СХЕМА ====================
    def _init_schema(self):
        self.c.executescript('''
            CREATE TABLE IF NOT EXISTS courses (
                id     INTEGER PRIMARY KEY,
                number INTEGER NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS groups (
                id        INTEGER PRIMARY KEY,
                name      TEXT    NOT NULL UNIQUE,
                students  INTEGER NOT NULL CHECK (students > 0),
                course_id INTEGER NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS auditoriums (
                id        INTEGER PRIMARY KEY,
                name      TEXT    NOT NULL UNIQUE,
                capacity  INTEGER NOT NULL CHECK (capacity > 0)
            );

            CREATE TABLE IF NOT EXISTS teachers (
                id   INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id   INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS teacher_subjects (
                teacher_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                PRIMARY KEY (teacher_id, subject_id),
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS course_subjects (
                course_id  INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                PRIMARY KEY (course_id, subject_id),
                FOREIGN KEY (course_id)  REFERENCES courses(id)  ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS distribution (
                id            INTEGER PRIMARY KEY,
                subject_id    INTEGER NOT NULL,
                group_id      INTEGER NOT NULL,
                auditorium_id INTEGER NOT NULL,
                FOREIGN KEY (subject_id)    REFERENCES subjects(id)    ON DELETE CASCADE,
                FOREIGN KEY (group_id)      REFERENCES groups(id)      ON DELETE CASCADE,
                FOREIGN KEY (auditorium_id) REFERENCES auditoriums(id) ON DELETE CASCADE,
                UNIQUE (subject_id, group_id)
            );
        ''')
        self.conn.commit()

    # ==================== КУРСЫ ====================
    def _get_or_create_course(self, number):
        self.c.execute("INSERT OR IGNORE INTO courses (number) VALUES (?)", (number,))
        self.c.execute("SELECT id FROM courses WHERE number = ?", (number,))
        return self.c.fetchone()["id"]

    # ==================== ГРУППЫ ====================
    def get_groups(self):
        self.c.execute('''
            SELECT g.id, g.name, g.students, c.number AS course
            FROM groups g JOIN courses c ON c.id = g.course_id
            ORDER BY c.number, g.name
        ''')
        return [dict(r) for r in self.c.fetchall()]

    def get_groups_by_course(self, course_number):
        self.c.execute('''
            SELECT g.id, g.name, g.students
            FROM groups g JOIN courses c ON c.id = g.course_id
            WHERE c.number = ?
            ORDER BY g.name
        ''', (course_number,))
        return [dict(r) for r in self.c.fetchall()]

    def add_group(self, name, students, course_number):
        cid = self._get_or_create_course(course_number)
        self.c.execute(
            "INSERT INTO groups (name, students, course_id) VALUES (?, ?, ?)",
            (name, students, cid)
        )
        self.conn.commit()
        return self.c.lastrowid

    def delete_group(self, gid):
        self.c.execute("DELETE FROM groups WHERE id = ?", (int(gid),))
        self.conn.commit()

    def clear_groups(self):
        self.c.execute("DELETE FROM groups")
        self.conn.commit()

    # ==================== АУДИТОРИИ ====================
    def get_auditoriums(self):
        self.c.execute("SELECT id, name, capacity FROM auditoriums ORDER BY name")
        return [dict(r) for r in self.c.fetchall()]

    def add_auditorium(self, name, capacity):
        self.c.execute(
            "INSERT INTO auditoriums (name, capacity) VALUES (?, ?)",
            (name, capacity)
        )
        self.conn.commit()
        return self.c.lastrowid

    def delete_auditorium(self, aid):
        self.c.execute("DELETE FROM auditoriums WHERE id = ?", (int(aid),))
        self.conn.commit()

    def clear_auditoriums(self):
        self.c.execute("DELETE FROM auditoriums")
        self.conn.commit()

    # ==================== ПРЕПОДАВАТЕЛИ ====================
    def get_teachers(self):
        self.c.execute("SELECT id, name FROM teachers ORDER BY name")
        return [dict(r) for r in self.c.fetchall()]

    def add_teacher(self, name):
        self.c.execute("INSERT INTO teachers (name) VALUES (?)", (name,))
        self.conn.commit()
        return self.c.lastrowid

    def delete_teacher(self, tid):
        self.c.execute("DELETE FROM teachers WHERE id = ?", (int(tid),))
        self.conn.commit()

    # ==================== ПРЕДМЕТЫ ====================
    def get_subjects(self):
        self.c.execute("SELECT id, name FROM subjects ORDER BY name")
        return [dict(r) for r in self.c.fetchall()]

    def add_subject(self, name):
        self.c.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
        self.conn.commit()
        return self.c.lastrowid

    def delete_subject(self, sid):
        self.c.execute("DELETE FROM subjects WHERE id = ?", (int(sid),))
        self.conn.commit()

    # ==================== ПРЕПОД ↔ ПРЕДМЕТ ====================
    def assign_teacher_subject(self, teacher_id, subject_id):
        self.c.execute(
            "INSERT OR IGNORE INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
            (int(teacher_id), int(subject_id))
        )
        self.conn.commit()

    def unassign_teacher_subject(self, teacher_id, subject_id):
        self.c.execute(
            "DELETE FROM teacher_subjects WHERE teacher_id = ? AND subject_id = ?",
            (int(teacher_id), int(subject_id))
        )
        self.conn.commit()

    def get_subjects_of_teacher(self, teacher_id):
        self.c.execute('''
            SELECT s.id, s.name FROM teacher_subjects ts
            JOIN subjects s ON s.id = ts.subject_id
            WHERE ts.teacher_id = ?
            ORDER BY s.name
        ''', (int(teacher_id),))
        return [dict(r) for r in self.c.fetchall()]

    # ==================== КУРС ↔ ПРЕДМЕТ ====================
    def add_course_subject(self, course_number, subject_id):
        cid = self._get_or_create_course(int(course_number))
        self.c.execute(
            "INSERT OR IGNORE INTO course_subjects (course_id, subject_id) VALUES (?, ?)",
            (cid, int(subject_id))
        )
        self.conn.commit()

    def remove_course_subject(self, course_number, subject_id):
        cid = self._get_or_create_course(int(course_number))
        self.c.execute(
            "DELETE FROM course_subjects WHERE course_id = ? AND subject_id = ?",
            (cid, int(subject_id))
        )
        self.conn.commit()

    def get_course_subjects(self, course_number):
        self.c.execute('''
            SELECT s.id, s.name FROM course_subjects cs
            JOIN courses  c ON c.id = cs.course_id
            JOIN subjects s ON s.id = cs.subject_id
            WHERE c.number = ?
            ORDER BY s.name
        ''', (int(course_number),))
        return [dict(r) for r in self.c.fetchall()]

    def get_courses_of_subject(self, subject_id):
        self.c.execute('''
            SELECT c.number FROM course_subjects cs
            JOIN courses c ON c.id = cs.course_id
            WHERE cs.subject_id = ?
            ORDER BY c.number
        ''', (int(subject_id),))
        return [r["number"] for r in self.c.fetchall()]

    # ==================== РАСПРЕДЕЛЕНИЕ ====================
    def save_distribution(self, subject_id, assignments):
        sid = int(subject_id)
        self.c.execute("DELETE FROM distribution WHERE subject_id = ?", (sid,))
        self.c.executemany(
            "INSERT INTO distribution (subject_id, group_id, auditorium_id) VALUES (?, ?, ?)",
            [(sid, int(g), int(a)) for g, a in assignments]
        )
        self.conn.commit()

    def load_distribution(self, subject_id):
        self.c.execute('''
            SELECT a.id AS aud_id, a.name AS aud_name, a.capacity,
                   g.id AS grp_id, g.name AS grp_name, g.students
            FROM distribution d
            JOIN auditoriums a ON a.id = d.auditorium_id
            JOIN groups      g ON g.id = d.group_id
            WHERE d.subject_id = ?
            ORDER BY a.name, g.name
        ''', (int(subject_id),))
        return [dict(r) for r in self.c.fetchall()]

    # ==================== СЛУЖЕБНОЕ ====================
    def close(self):
        self.conn.close()