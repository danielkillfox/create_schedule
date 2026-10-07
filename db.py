
import sqlite3
from contextlib import contextmanager
from typing import Optional

from distributor import Group, Auditorium


KIND_LECTURE = "lecture"
KIND_PRACTICE = "practice"


class DB:
    def __init__(self, path: str = "schedule.db"):
        self.conn: Optional[sqlite3.Connection] = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.c = self.conn.cursor()
        self._course_cache: dict[int, int] = {}
        self._init_schema()

    # ==================== СХЕМА ====================
    def _init_schema(self) -> None:
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
                capacity  INTEGER NOT NULL CHECK (capacity > 0),
                kind      TEXT    NOT NULL DEFAULT 'lecture'
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

            CREATE TABLE IF NOT EXISTS teacher_auditoriums (
                teacher_id    INTEGER NOT NULL,
                auditorium_id INTEGER NOT NULL,
                PRIMARY KEY (teacher_id, auditorium_id),
                FOREIGN KEY (teacher_id)    REFERENCES teachers(id)    ON DELETE CASCADE,
                FOREIGN KEY (auditorium_id) REFERENCES auditoriums(id) ON DELETE CASCADE
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
                pair_number   INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (subject_id)    REFERENCES subjects(id)    ON DELETE CASCADE,
                FOREIGN KEY (group_id)      REFERENCES groups(id)      ON DELETE CASCADE,
                FOREIGN KEY (auditorium_id) REFERENCES auditoriums(id) ON DELETE CASCADE,
                UNIQUE (subject_id, group_id)
            );

            CREATE TABLE IF NOT EXISTS schedule (
                id            INTEGER PRIMARY KEY,
                teacher_id    INTEGER NOT NULL,
                subject_id    INTEGER,
                group_id      INTEGER NOT NULL,
                auditorium_id INTEGER NOT NULL,
                kind          TEXT    NOT NULL DEFAULT 'lecture',
                pair_number   INTEGER NOT NULL DEFAULT 1,
                weekday       INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (teacher_id)    REFERENCES teachers(id)    ON DELETE CASCADE,
                FOREIGN KEY (subject_id)    REFERENCES subjects(id)    ON DELETE SET NULL,
                FOREIGN KEY (group_id)      REFERENCES groups(id)      ON DELETE CASCADE,
                FOREIGN KEY (auditorium_id) REFERENCES auditoriums(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_groups_course ON groups(course_id);
            CREATE INDEX IF NOT EXISTS idx_dist_subject  ON distribution(subject_id);
            CREATE INDEX IF NOT EXISTS idx_dist_aud      ON distribution(auditorium_id);
            CREATE INDEX IF NOT EXISTS idx_dist_group    ON distribution(group_id);
            CREATE INDEX IF NOT EXISTS idx_cs_course     ON course_subjects(course_id);
            CREATE INDEX IF NOT EXISTS idx_ts_teacher    ON teacher_subjects(teacher_id);
            CREATE INDEX IF NOT EXISTS idx_ta_teacher    ON teacher_auditoriums(teacher_id);
            CREATE INDEX IF NOT EXISTS idx_sched_teacher ON schedule(teacher_id);
        ''')
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        """Догоняем схему, если БД создана старой версией."""
        def cols(table: str) -> set[str]:
            return {r["name"] for r in self.c.execute(f"PRAGMA table_info({table})").fetchall()}

        if "kind" not in cols("auditoriums"):
            self.c.execute(
                "ALTER TABLE auditoriums ADD COLUMN kind TEXT NOT NULL DEFAULT 'lecture'"
            )
        if "pair_number" not in cols("distribution"):
            self.c.execute(
                "ALTER TABLE distribution ADD COLUMN pair_number INTEGER NOT NULL DEFAULT 1"
            )
        if "pair_number" not in cols("schedule"):
            self.c.execute(
                "ALTER TABLE schedule ADD COLUMN pair_number INTEGER NOT NULL DEFAULT 1"
            )
        if "weekday" not in cols("schedule"):
            self.c.execute(
                "ALTER TABLE schedule ADD COLUMN weekday INTEGER NOT NULL DEFAULT 0"
            )

    # ==================== фууу ТРАНЗАКЦИИ ====================

    @contextmanager
    def _tx(self):
        try:
            yield self.c
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # ==================== КУРСЫ =================
    def _get_or_create_course(self, number: int) -> int:
        number = int(number)
        cached = self._course_cache.get(number)
        if cached is not None:
            return cached
        self.c.execute("INSERT OR IGNORE INTO courses (number) VALUES (?)", (number,))
        self.c.execute("SELECT id FROM courses WHERE number = ?", (number,))
        cid = self.c.fetchone()["id"]
        self._course_cache[number] = cid
        return cid

    # ================ ГРУППЫ ====================
    def get_groups(self) -> list[dict]:
        self.c.execute('''
            SELECT g.id, g.name, g.students, c.number AS course
            FROM groups g JOIN courses c ON c.id = g.course_id
            ORDER BY c.number, g.name
        ''')
        return [dict(r) for r in self.c.fetchall()]

    def get_groups_by_course(self, course_number: int) -> list[Group]:
        self.c.execute('''
            SELECT g.id, g.name, g.students
            FROM groups g JOIN courses c ON c.id = g.course_id
            WHERE c.number = ?
            ORDER BY g.name
        ''', (int(course_number),))
        return [Group(id=r["id"], name=r["name"], students=r["students"])
                for r in self.c.fetchall()]

    def add_group(self, name: str, students: int, course_number: int) -> int:
        cid = self._get_or_create_course(course_number)
        with self._tx():
            self.c.execute(
                "INSERT INTO groups (name, students, course_id) VALUES (?, ?, ?)",
                (name, students, cid),
            )
        return self.c.lastrowid

    def delete_group(self, gid: int) -> None:
        with self._tx():
            self.c.execute("DELETE FROM groups WHERE id = ?", (int(gid),))

    def clear_groups(self) -> None:
        with self._tx():
            self.c.execute("DELETE FROM groups")

    def update_group(self, gid: int, name: str, students: int, course_number: int) -> None:
        cid = self._get_or_create_course(int(course_number))
        with self._tx():
            self.c.execute(
                "UPDATE groups SET name = ?, students = ?, course_id = ? WHERE id = ?",
                (name, int(students), cid, int(gid)),
            )

    # ================== АУДИТОРИИ =================
    def get_auditoriums(self) -> list[Auditorium]:
        self.c.execute("SELECT id, name, capacity, kind FROM auditoriums ORDER BY name")
        return [Auditorium(id=r["id"], name=r["name"],
                           capacity=r["capacity"], kind=r["kind"])
                for r in self.c.fetchall()]

    def add_auditorium(self, name: str, capacity: int, kind: str = KIND_LECTURE) -> int:
        if kind not in (KIND_LECTURE, KIND_PRACTICE):
            raise ValueError(f"Некорректный тип аудитории: {kind!r}")
        with self._tx():
            self.c.execute(
                "INSERT INTO auditoriums (name, capacity, kind) VALUES (?, ?, ?)",
                (name, capacity, kind),
            )
        return self.c.lastrowid

    def update_auditorium_kind(self, aid: int, kind: str) -> None:
        if kind not in (KIND_LECTURE, KIND_PRACTICE):
            raise ValueError(f"Некорректный тип аудитории: {kind!r}")
        with self._tx():
            self.c.execute("UPDATE auditoriums SET kind = ? WHERE id = ?", (kind, int(aid)))

    def update_auditorium(self, aid: int, name: str, capacity: int) -> None:
        with self._tx():
            self.c.execute(
                "UPDATE auditoriums SET name = ?, capacity = ? WHERE id = ?",
                (name, int(capacity), int(aid)),
            )

    def delete_auditorium(self, aid: int) -> None:
        with self._tx():
            self.c.execute("DELETE FROM auditoriums WHERE id = ?", (int(aid),))

    def clear_auditoriums(self) -> None:
        with self._tx():
            self.c.execute("DELETE FROM auditoriums")

    # =============== ПРЕПОДАВАТЕЛИ ==================
    def get_teachers(self) -> list[dict]:
        self.c.execute("SELECT id, name FROM teachers ORDER BY name")
        return [dict(r) for r in self.c.fetchall()]

    def add_teacher(self, name: str) -> int:
        with self._tx():
            self.c.execute("INSERT INTO teachers (name) VALUES (?)", (name,))
        return self.c.lastrowid

    def delete_teacher(self, tid: int) -> None:
        with self._tx():
            self.c.execute("DELETE FROM teachers WHERE id = ?", (int(tid),))

    # ================= ПРЕДМЕТЫ =================
    def get_subjects(self) -> list[dict]:
        self.c.execute("SELECT id, name FROM subjects ORDER BY name")
        return [dict(r) for r in self.c.fetchall()]

    def add_subject(self, name: str) -> int:
        with self._tx():
            self.c.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
        return self.c.lastrowid

    def delete_subject(self, sid: int) -> None:
        with self._tx():
            self.c.execute("DELETE FROM subjects WHERE id = ?", (int(sid),))

    # ================= ПРЕПОД - ПРЕДМЕТ ================
    def assign_teacher_subject(self, teacher_id: int, subject_id: int) -> None:
        with self._tx():
            self.c.execute(
                "INSERT OR IGNORE INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
                (int(teacher_id), int(subject_id)),
            )

    def unassign_teacher_subject(self, teacher_id: int, subject_id: int) -> None:
        with self._tx():
            self.c.execute(
                "DELETE FROM teacher_subjects WHERE teacher_id = ? AND subject_id = ?",
                (int(teacher_id), int(subject_id)),
            )

    def get_subjects_of_teacher(self, teacher_id: int) -> list[dict]:
        self.c.execute('''
            SELECT s.id, s.name FROM teacher_subjects ts
            JOIN subjects s ON s.id = ts.subject_id
            WHERE ts.teacher_id = ?
            ORDER BY s.name
        ''', (int(teacher_id),))
        return [dict(r) for r in self.c.fetchall()]

    def get_teachers_of_subject(self, subject_id: int) -> list[dict]:
        self.c.execute('''
            SELECT t.id, t.name FROM teacher_subjects ts
            JOIN teachers t ON t.id = ts.teacher_id
            WHERE ts.subject_id = ?
            ORDER BY t.name
        ''', (int(subject_id),))
        return [dict(r) for r in self.c.fetchall()]

    # ================= ПРЕПОД - АУДИТОРИЯ ==================
    def assign_teacher_auditorium(self, teacher_id: int, auditorium_id: int) -> None:
        with self._tx():
            self.c.execute(
                "INSERT OR IGNORE INTO teacher_auditoriums (teacher_id, auditorium_id) VALUES (?, ?)",
                (int(teacher_id), int(auditorium_id)),
            )

    def unassign_teacher_auditorium(self, teacher_id: int, auditorium_id: int) -> None:
        with self._tx():
            self.c.execute(
                "DELETE FROM teacher_auditoriums WHERE teacher_id = ? AND auditorium_id = ?",
                (int(teacher_id), int(auditorium_id)),
            )

    def get_auditoriums_of_teacher(self, teacher_id: int) -> list[Auditorium]:
        self.c.execute('''
            SELECT a.id, a.name, a.capacity, a.kind
            FROM teacher_auditoriums ta
            JOIN auditoriums a ON a.id = ta.auditorium_id
            WHERE ta.teacher_id = ?
            ORDER BY a.name
        ''', (int(teacher_id),))
        return [Auditorium(id=r["id"], name=r["name"],
                           capacity=r["capacity"], kind=r["kind"])
                for r in self.c.fetchall()]

    # ================= КУРС - ПРЕДМЕТ ==================
    def add_course_subject(self, course_number: int, subject_id: int) -> None:
        cid = self._get_or_create_course(int(course_number))
        with self._tx():
            self.c.execute(
                "INSERT OR IGNORE INTO course_subjects (course_id, subject_id) VALUES (?, ?)",
                (cid, int(subject_id)),
            )

    def remove_course_subject(self, course_number: int, subject_id: int) -> None:
        cid = self._get_or_create_course(int(course_number))
        with self._tx():
            self.c.execute(
                "DELETE FROM course_subjects WHERE course_id = ? AND subject_id = ?",
                (cid, int(subject_id)),
            )

    def get_course_subjects(self, course_number: int) -> list[dict]:
        self.c.execute('''
            SELECT s.id, s.name FROM course_subjects cs
            JOIN courses  c ON c.id = cs.course_id
            JOIN subjects s ON s.id = cs.subject_id
            WHERE c.number = ?
            ORDER BY s.name
        ''', (int(course_number),))
        return [dict(r) for r in self.c.fetchall()]

    def get_courses_of_subject(self, subject_id: int) -> list[int]:
        self.c.execute('''
            SELECT c.number FROM course_subjects cs
            JOIN courses c ON c.id = cs.course_id
            WHERE cs.subject_id = ?
            ORDER BY c.number
        ''', (int(subject_id),))
        return [r["number"] for r in self.c.fetchall()]

    # ==================== РАСПРЕДЕЛЕНИЕ (черновик) ====================
    def save_distribution(
        self,
        subject_id: int,
        assignments: list[tuple[int, int, int]],
    ) -> None:
        """assignments: список (group_id, auditorium_id, pair_number)."""
        sid = int(subject_id)
        with self._tx():
            self.c.execute("DELETE FROM distribution WHERE subject_id = ?", (sid,))
            if assignments:
                self.c.executemany(
                    "INSERT INTO distribution "
                    "(subject_id, group_id, auditorium_id, pair_number) "
                    "VALUES (?, ?, ?, ?)",
                    [(sid, int(g), int(a), int(p)) for g, a, p in assignments],
                )

    def load_distribution(self, subject_id: int) -> list[dict]:
        self.c.execute('''
            SELECT a.id AS aud_id, a.name AS aud_name, a.capacity,
                   g.id AS grp_id, g.name AS grp_name, g.students,
                   d.pair_number
            FROM distribution d
            JOIN auditoriums a ON a.id = d.auditorium_id
            JOIN groups      g ON g.id = d.group_id
            WHERE d.subject_id = ?
            ORDER BY d.pair_number, a.name, g.name
        ''', (int(subject_id),))
        return [dict(r) for r in self.c.fetchall()]

    # ==================== РАСПИСАНИЕ ПРЕПОДАВАТЕЛЯ ====================
    def save_schedule(
        self,
        teacher_id: int,
        subject_id: Optional[int],
        kind: str,
        assignments: list[tuple[int, int, int]],
        weekday: int = 0,
    ) -> int:
        """
        ДОБАВЛЯЕТ занятия в расписание преподавателя (не перезаписывает).

        assignments: список (group_id, auditorium_id, pair_number)
            или (group_id, auditorium_id, pair_number, weekday).

        Точные дубли (тот же препод + предмет + тип + группа + аудитория + ячейка + день)
        пропускаются — чтобы повторное нажатие «Записать в расписание» не создавало
        копии. Всё остальное добавляется к уже существующему расписанию.

        Возвращает количество фактически добавленных строк.
        """
        if kind not in (KIND_LECTURE, KIND_PRACTICE):
            raise ValueError(f"Некорректный тип занятия: {kind!r}")
        tid = int(teacher_id)
        sid = int(subject_id) if subject_id is not None else None

        # Нормализуем assignments к (group, aud, pair, weekday)
        normalized: list[tuple[int, int, int, int]] = []
        for a in assignments:
            if len(a) == 4:
                g, au, p, w = a
                normalized.append((int(g), int(au), int(p), int(w)))
            else:
                g, au, p = a
                normalized.append((int(g), int(au), int(p), int(weekday)))

        with self._tx():
            # Уже записанные тройки (group, aud, cell, weekday) для этого препод+предмет+тип
            if sid is None:
                self.c.execute(
                    "SELECT group_id, auditorium_id, pair_number, weekday FROM schedule "
                    "WHERE teacher_id = ? AND kind = ? AND subject_id IS NULL",
                    (tid, kind),
                )
            else:
                self.c.execute(
                    "SELECT group_id, auditorium_id, pair_number, weekday FROM schedule "
                    "WHERE teacher_id = ? AND kind = ? AND subject_id = ?",
                    (tid, kind, sid),
                )
            existing = {
                (int(r["group_id"]), int(r["auditorium_id"]),
                 int(r["pair_number"]), int(r["weekday"]))
                for r in self.c.fetchall()
            }

            to_insert = [
                (tid, sid, int(g), int(a), kind, int(p), int(w))
                for (g, a, p, w) in normalized
                if (int(g), int(a), int(p), int(w)) not in existing
            ]

            if to_insert:
                self.c.executemany(
                    "INSERT INTO schedule "
                    "(teacher_id, subject_id, group_id, auditorium_id, kind, pair_number, weekday) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    to_insert,
                )

        return len(to_insert)

    def get_teacher_schedule(self, teacher_id: int) -> list[dict]:
        self.c.execute('''
            SELECT s.id, s.kind, s.pair_number, s.weekday, s.subject_id,
                   sub.name AS subject_name,
                   g.name   AS group_name, g.students,
                   a.name   AS aud_name,   a.capacity
            FROM schedule s
            LEFT JOIN subjects sub ON sub.id = s.subject_id
            JOIN groups      g ON g.id = s.group_id
            JOIN auditoriums a ON a.id = s.auditorium_id
            WHERE s.teacher_id = ?
            ORDER BY s.id
        ''', (int(teacher_id),))
        return [dict(r) for r in self.c.fetchall()]

    def update_schedule_weekday(self, ids: list[int], weekday: int) -> None:
        """Меняет день недели (0=Пн..4=Пт) для указанных строк расписания."""
        if not ids:
            return
        weekday = int(weekday)
        if weekday not in (0, 1, 2, 3, 4):
            raise ValueError(f"Некорректный день недели: {weekday!r}")
        with self._tx():
            self.c.executemany(
                "UPDATE schedule SET weekday = ? WHERE id = ?",
                [(weekday, int(i)) for i in ids],
            )

    def clear_teacher_schedule(self, teacher_id: int) -> None:
        with self._tx():
            self.c.execute("DELETE FROM schedule WHERE teacher_id = ?", (int(teacher_id),))

    def delete_schedule_rows(self, ids: list[int]) -> None:
        """Удаляет выбранные строки расписания по их id."""
        if not ids:
            return
        with self._tx():
            self.c.executemany(
                "DELETE FROM schedule WHERE id = ?",
                [(int(i),) for i in ids],
            )

    # ==================== СЛУЖЕБНОЕ ====================
    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None