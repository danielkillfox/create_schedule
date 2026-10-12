
import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).with_name("settings.json")

RU = "ru"
EN = "en"
ES = "es"
IT = "it"
DE = "de"
FR = "fr"
ZH = "zh"

LANGUAGE_NAMES = {
    RU: "Русский",
    EN: "English",
    ES: "Español",
    IT: "Italiano",
    DE: "Deutsch",
    FR: "Français",
    ZH: "中文",
}

SUPPORTED = (RU, EN, ES, IT, DE, FR, ZH)

_current: str = RU


def _load_saved() -> str:
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        code = str(data.get("language", RU)).lower()
    except (OSError, ValueError, AttributeError):
        return RU
    return code if code in SUPPORTED else RU


_current = _load_saved()


def get_language() -> str:
    return _current


def set_language(code: str) -> str:
    global _current
    code = str(code).lower()
    if code not in SUPPORTED:
        code = RU
    _current = code
    try:
        SETTINGS_PATH.write_text(
            json.dumps({"language": code}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
    return _current


TEXTS: dict[str, dict[str, str]] = {
    "app_title": {
        RU: "Распределение групп по аудиториям и парам",
        EN: "Group-to-room and lesson scheduler",
        ES: "Distribución de grupos por aulas y clases",
        IT: "Distribuzione dei gruppi per aule e lezioni",
        DE: "Verteilung von Gruppen auf Räume und Stunden",
        FR: "Répartition des groupes par salles et séances",
        ZH: "班级教室与课程分配",
    },
    "tab_groups": {RU: "1. Группы", EN: "1. Groups", ES: "1. Grupos", IT: "1. Gruppi", DE: "1. Gruppen", FR: "1. Groupes", ZH: "1. 班级"},
    "tab_auds": {RU: "2. Аудитории", EN: "2. Rooms", ES: "2. Aulas", IT: "2. Aule", DE: "2. Räume", FR: "2. Salles", ZH: "2. 教室"},
    "tab_teachers": {RU: "3. Преподаватели", EN: "3. Teachers", ES: "3. Profesores", IT: "3. Docenti", DE: "3. Lehrkräfte", FR: "3. Enseignants", ZH: "3. 教师"},
    "tab_subjects": {RU: "4. Предметы", EN: "4. Subjects", ES: "4. Asignaturas", IT: "4. Materie", DE: "4. Fächer", FR: "4. Matières", ZH: "4. 科目"},
    "tab_distribute": {RU: "5. Распределение", EN: "5. Allocation", ES: "5. Distribución", IT: "5. Distribuzione", DE: "5. Verteilung", FR: "5. Répartition", ZH: "5. 分配"},
    "tab_schedule": {RU: "6. Расписание", EN: "6. Timetable", ES: "6. Horario", IT: "6. Orario", DE: "6. Stundenplan", FR: "6. Emploi du temps", ZH: "6. 课程表"},
    "tab_calendar": {RU: "7. Таблица", EN: "7. Grid", ES: "7. Tabla", IT: "7. Tabella", DE: "7. Tabelle", FR: "7. Tableau", ZH: "7. 表格"},
    "tab_settings": {RU: "8. Настройки", EN: "8. Settings", ES: "8. Ajustes", IT: "8. Impostazioni", DE: "8. Einstellungen", FR: "8. Paramètres", ZH: "8. 设置"},

    "btn_export": {RU: "Экспорт в Excel", EN: "Export to Excel", ES: "Exportar a Excel", IT: "Esporta in Excel", DE: "Nach Excel exportieren", FR: "Exporter vers Excel", ZH: "导出到 Excel"},
    "btn_export_tip": {
        RU: "Выгрузить все данные в файл .xlsx",
        EN: "Save all data to an .xlsx file",
        ES: "Guardar todos los datos en un archivo .xlsx",
        IT: "Salva tutti i dati in un file .xlsx",
        DE: "Alle Daten in eine .xlsx-Datei speichern",
        FR: "Enregistrer toutes les données dans un fichier .xlsx",
        ZH: "将所有数据保存到 .xlsx 文件",
    },
    "btn_import": {RU: "Импорт из Excel", EN: "Import from Excel", ES: "Importar desde Excel", IT: "Importa da Excel", DE: "Aus Excel importieren", FR: "Importer depuis Excel", ZH: "从 Excel 导入"},
    "btn_import_tip": {
        RU: "Загрузить данные из файла .xlsx",
        EN: "Load data from an .xlsx file",
        ES: "Cargar datos desde un archivo .xlsx",
        IT: "Carica i dati da un file .xlsx",
        DE: "Daten aus einer .xlsx-Datei laden",
        FR: "Charger les données depuis un fichier .xlsx",
        ZH: "从 .xlsx 文件加载数据",
    },

    "lbl_name": {RU: "Название:", EN: "Name:", ES: "Nombre:", IT: "Nome:", DE: "Name:", FR: "Nom :", ZH: "名称："},
    "lbl_person": {RU: "Имя:", EN: "Name:", ES: "Nombre:", IT: "Nome:", DE: "Name:", FR: "Nom :", ZH: "姓名："},
    "btn_add": {RU: "Добавить", EN: "Add", ES: "Añadir", IT: "Aggiungi", DE: "Hinzufügen", FR: "Ajouter", ZH: "添加"},
    "btn_delete_sel": {RU: "Удалить выбранную", EN: "Delete selected", ES: "Eliminar selección", IT: "Elimina selezionata", DE: "Auswahl löschen", FR: "Supprimer la sélection", ZH: "删除所选"},
    "btn_reload": {RU: "Обновить из БД", EN: "Reload from DB", ES: "Recargar", IT: "Ricarica", DE: "Aus DB neu laden", FR: "Recharger", ZH: "从数据库刷新"},
    "btn_refresh": {RU: "Обновить", EN: "Refresh", ES: "Actualizar", IT: "Aggiorna", DE: "Aktualisieren", FR: "Actualiser", ZH: "刷新"},
    "lbl_bind": {RU: "Привязать:", EN: "Link:", ES: "Vincular:", IT: "Collega:", DE: "Verknüpfen:", FR: "Associer :", ZH: "关联："},
    "btn_bind": {RU: "Привязать", EN: "Link", ES: "Vincular", IT: "Collega", DE: "Verknüpfen", FR: "Associer", ZH: "关联"},

    "box_add_group": {RU: "Добавить группу", EN: "Add a group", ES: "Añadir un grupo", IT: "Aggiungi un gruppo", DE: "Gruppe hinzufügen", FR: "Ajouter un groupe", ZH: "添加班级"},
    "lbl_students": {RU: "Студентов:", EN: "Students:", ES: "Estudiantes:", IT: "Studenti:", DE: "Studierende:", FR: "Étudiants :", ZH: "学生人数："},
    "lbl_course": {RU: "Курс:", EN: "Year:", ES: "Curso:", IT: "Anno:", DE: "Jahr:", FR: "Année :", ZH: "年级："},
    "lbl_groups_list": {RU: "Список групп:", EN: "Group list:", ES: "Lista de grupos:", IT: "Elenco dei gruppi:", DE: "Gruppenliste:", FR: "Liste des groupes :", ZH: "班级列表："},
    "hdr_group": {RU: "Группа", EN: "Group", ES: "Grupo", IT: "Gruppo", DE: "Gruppe", FR: "Groupe", ZH: "班级"},
    "hdr_people": {RU: "Кол-во людей", EN: "People", ES: "Personas", IT: "Persone", DE: "Personen", FR: "Personnes", ZH: "人数"},
    "hdr_course": {RU: "Курс", EN: "Year", ES: "Curso", IT: "Anno", DE: "Jahr", FR: "Année", ZH: "年级"},
    "btn_clear_groups": {RU: "Очистить все группы", EN: "Clear all groups", ES: "Borrar grupos", IT: "Cancella i gruppi", DE: "Alle Gruppen löschen", FR: "Effacer les groupes", ZH: "清空所有班级"},

    "box_add_aud": {RU: "Добавить аудиторию", EN: "Add a room", ES: "Añadir un aula", IT: "Aggiungi un'aula", DE: "Raum hinzufügen", FR: "Ajouter une salle", ZH: "添加教室"},
    "lbl_capacity": {RU: "Вместимость:", EN: "Capacity:", ES: "Capacidad:", IT: "Capienza:", DE: "Kapazität:", FR: "Capacité :", ZH: "容量："},
    "lbl_type": {RU: "Тип:", EN: "Type:", ES: "Tipo:", IT: "Tipo:", DE: "Typ:", FR: "Type :", ZH: "类型："},
    "lbl_auds_list": {RU: "Список аудиторий:", EN: "Room list:", ES: "Lista de aulas:", IT: "Elenco delle aule:", DE: "Raumliste:", FR: "Liste des salles :", ZH: "教室列表："},
    "hdr_aud": {RU: "Аудитория", EN: "Room", ES: "Aula", IT: "Aula", DE: "Raum", FR: "Salle", ZH: "教室"},
    "hdr_capacity": {RU: "Вместимость", EN: "Capacity", ES: "Capacidad", IT: "Capienza", DE: "Kapazität", FR: "Capacité", ZH: "容量"},
    "hdr_type": {RU: "Тип", EN: "Type", ES: "Tipo", IT: "Tipo", DE: "Typ", FR: "Type", ZH: "类型"},
    "btn_clear_auds": {RU: "Очистить все аудитории", EN: "Clear all rooms", ES: "Borrar aulas", IT: "Cancella le aule", DE: "Alle Räume löschen", FR: "Effacer les salles", ZH: "清空所有教室"},

    "box_add_teacher": {RU: "Добавить преподавателя", EN: "Add a teacher", ES: "Añadir un profesor", IT: "Aggiungi un docente", DE: "Lehrkraft hinzufügen", FR: "Ajouter un enseignant", ZH: "添加教师"},
    "lbl_teachers": {RU: "Преподаватели:", EN: "Teachers:", ES: "Profesores:", IT: "Docenti:", DE: "Lehrkräfte:", FR: "Enseignants :", ZH: "教师："},
    "hdr_teacher_name": {RU: "Имя", EN: "Name", ES: "Nombre", IT: "Nome", DE: "Name", FR: "Nom", ZH: "姓名"},
    "btn_del_teacher": {RU: "Удалить преподавателя", EN: "Delete teacher", ES: "Eliminar profesor", IT: "Elimina docente", DE: "Lehrkraft löschen", FR: "Supprimer l'enseignant", ZH: "删除教师"},
    "lbl_teacher_subjects": {RU: "Предметы преподавателя:", EN: "Teacher's subjects:", ES: "Asignaturas:", IT: "Materie del docente:", DE: "Fächer der Lehrkraft:", FR: "Matières de l'enseignant :", ZH: "教师的科目："},
    "hdr_subject_name": {RU: "Предмет", EN: "Subject", ES: "Asignatura", IT: "Materia", DE: "Fach", FR: "Matière", ZH: "科目"},
    "btn_unbind_subject": {RU: "Отвязать выбранный предмет", EN: "Unlink subject", ES: "Desvincular", IT: "Scollega materia", DE: "Fach trennen", FR: "Dissocier la matière", ZH: "取消关联科目"},
    "lbl_teacher_auds": {RU: "Аудитории преподавателя:", EN: "Teacher's rooms:", ES: "Aulas:", IT: "Aule del docente:", DE: "Räume der Lehrkraft:", FR: "Salles de l'enseignant :", ZH: "教师的教室："},
    "hdr_aud_name": {RU: "Аудитория", EN: "Room", ES: "Aula", IT: "Aula", DE: "Raum", FR: "Salle", ZH: "教室"},
    "btn_unbind_aud": {RU: "Отвязать выбранную аудиторию", EN: "Unlink room", ES: "Desvincular aula", IT: "Scollega aula", DE: "Raum trennen", FR: "Dissocier la salle", ZH: "取消关联教室"},

    "box_add_subject": {RU: "Добавить предмет", EN: "Add a subject", ES: "Añadir asignatura", IT: "Aggiungi materia", DE: "Fach hinzufügen", FR: "Ajouter une matière", ZH: "添加科目"},
    "lbl_subjects": {RU: "Предметы:", EN: "Subjects:", ES: "Asignaturas:", IT: "Materie:", DE: "Fächer:", FR: "Matières :", ZH: "科目："},
    "btn_del_subject": {RU: "Удалить предмет", EN: "Delete subject", ES: "Eliminar asignatura", IT: "Elimina materia", DE: "Fach löschen", FR: "Supprimer la matière", ZH: "删除科目"},
    "lbl_subject_courses": {RU: "Привязанные курсы", EN: "Linked years", ES: "Cursos vinculados", IT: "Anni collegati", DE: "Verknüpfte Jahre", FR: "Années liées", ZH: "关联的年级"},
    "hdr_subject_title": {RU: "Название", EN: "Title", ES: "Nombre", IT: "Nome", DE: "Titel", FR: "Titre", ZH: "名称"},
    "hdr_course_col": {RU: "Курс", EN: "Year", ES: "Curso", IT: "Anno", DE: "Jahr", FR: "Année", ZH: "年级"},
    "lbl_add_course": {RU: "Добавить курс:", EN: "Add year:", ES: "Añadir curso:", IT: "Aggiungi anno:", DE: "Jahr hinzufügen:", FR: "Ajouter une année :", ZH: "添加年级："},
    "btn_remove_course": {RU: "Убрать выбранный курс", EN: "Remove year", ES: "Quitar curso", IT: "Rimuovi anno", DE: "Jahr entfernen", FR: "Retirer l'année", ZH: "移除所选年级"},

    "box_params": {RU: "Параметры распределения", EN: "Allocation settings", ES: "Parámetros", IT: "Parametri", DE: "Verteilungseinstellungen", FR: "Paramètres de répartition", ZH: "分配参数"},
    "lbl_course_col": {RU: "Курс:", EN: "Year:", ES: "Curso:", IT: "Anno:", DE: "Jahr:", FR: "Année :", ZH: "年级："},
    "lbl_subject_col": {RU: "Предмет:", EN: "Subject:", ES: "Asignatura:", IT: "Materia:", DE: "Fach:", FR: "Matière :", ZH: "科目："},
    "lbl_teacher_col": {RU: "Преподаватель:", EN: "Teacher:", ES: "Profesor:", IT: "Docente:", DE: "Lehrkraft:", FR: "Enseignant :", ZH: "教师："},
    "lbl_kind_col": {RU: "Тип занятия:", EN: "Lesson type:", ES: "Tipo de clase:", IT: "Tipo di lezione:", DE: "Unterrichtstyp:", FR: "Type de séance :", ZH: "课程类型："},
    "kind_lecture": {RU: "Лекция", EN: "Lecture", ES: "Conferencia", IT: "Lezione", DE: "Vorlesung", FR: "Cours magistral", ZH: "讲座"},
    "kind_practice": {RU: "Практика", EN: "Practical", ES: "Práctica", IT: "Esercitazione", DE: "Übung", FR: "Travaux pratiques", ZH: "实践课"},
    "lbl_filter": {RU: "Фильтр:", EN: "Filter:", ES: "Filtro:", IT: "Filtro:", DE: "Filter:", FR: "Filtre :", ZH: "筛选："},
    "chk_max2": {RU: "Не больше 2 лекций в день", EN: "Max 2 lectures per day", ES: "Máx. 2 conferencias al día", IT: "Max 2 lezioni al giorno", DE: "Max. 2 Vorlesungen pro Tag", FR: "Max 2 cours magistraux par jour", ZH: "每天最多2节讲座"},
    "chk_max2_tip": {
        RU: "При генерации лекции преподавателя раскладываются по дням Пн–Пт так, чтобы в один день было не больше 2 лекций (учитывается уже записанное расписание). Действует только для лекций.",
        EN: "Lectures are spread across Mon–Fri so there are no more than 2 lectures per day (existing timetable is taken into account). Lectures only.",
        ES: "Las conferencias se reparten de lun. a vie. con un máximo de 2 al día (se tiene en cuenta el horario existente). Solo conferencias.",
        IT: "Le lezioni sono distribuite da lun. a ven. con un massimo di 2 al giorno (si tiene conto dell'orario esistente). Solo lezioni.",
        DE: "Vorlesungen werden auf Mo–Fr verteilt, höchstens 2 pro Tag (der bestehende Stundenplan wird berücksichtigt). Nur für Vorlesungen.",
        FR: "Les cours magistraux sont répartis sur lun–ven, max 2 par jour (l'emploi du temps existant est pris en compte). Cours magistraux uniquement.",
        ZH: "讲座将分布在周一至周五，每天最多2节（考虑已有课程表）。仅适用于讲座。",
    },
    "box_groups": {RU: "Группы", EN: "Groups", ES: "Grupos", IT: "Gruppi", DE: "Gruppen", FR: "Groupes", ZH: "班级"},
    "hdr_tick": {RU: "", EN: "", ES: "", IT: "", DE: "", FR: "", ZH: ""},
    "hdr_group_col": {RU: "Группа", EN: "Group", ES: "Grupo", IT: "Gruppo", DE: "Gruppe", FR: "Groupe", ZH: "班级"},
    "hdr_people_col": {RU: "Человек", EN: "People", ES: "Personas", IT: "Persone", DE: "Personen", FR: "Personnes", ZH: "人数"},
    "btn_run": {RU: "Распределить по ячейкам", EN: "Allocate to slots", ES: "Distribuir", IT: "Distribuisci", DE: "Auf Slots verteilen", FR: "Répartir", ZH: "分配到时间段"},
    "btn_save": {RU: "Записать в расписание", EN: "Save to timetable", ES: "Guardar en horario", IT: "Salva nell'orario", DE: "In Stundenplan speichern", FR: "Enregistrer", ZH: "保存到课程表"},
    "btn_auto": {
        RU: "Распределить и сразу записать в расписание",
        EN: "Allocate and save to timetable",
        ES: "Distribuir y guardar en horario",
        IT: "Distribuisci e salva nell'orario",
        DE: "Verteilen und speichern",
        FR: "Répartir et enregistrer",
        ZH: "分配并保存到课程表",
    },
    "box_result": {RU: "Результат", EN: "Result", ES: "Resultado", IT: "Risultato", DE: "Ergebnis", FR: "Résultat", ZH: "结果"},
    "btn_show_text": {RU: "Показать текст", EN: "Show text", ES: "Mostrar texto", IT: "Mostra testo", DE: "Text anzeigen", FR: "Afficher le texte", ZH: "显示文本"},
    "btn_show_table": {RU: "Показать таблицу", EN: "Show table", ES: "Mostrar tabla", IT: "Mostra tabella", DE: "Tabelle anzeigen", FR: "Afficher le tableau", ZH: "显示表格"},
    "hdr_cell": {RU: "Ячейка", EN: "Slot", ES: "Casilla", IT: "Slot", DE: "Slot", FR: "Case", ZH: "时间段"},
    "hdr_aud_col": {RU: "Аудитория", EN: "Room", ES: "Aula", IT: "Aula", DE: "Raum", FR: "Salle", ZH: "教室"},
    "hdr_groups_col": {RU: "Группы", EN: "Groups", ES: "Grupos", IT: "Gruppi", DE: "Gruppen", FR: "Groupes", ZH: "班级"},
    "hdr_filled": {RU: "Заполнено", EN: "Filled", ES: "Ocupado", IT: "Riempito", DE: "Belegt", FR: "Rempli", ZH: "已占用"},
    "hdr_progress": {RU: "Прогресс", EN: "Progress", ES: "Progreso", IT: "Progresso", DE: "Fortschritt", FR: "Progrès", ZH: "进度"},
    "no_teacher": {RU: "— не выбран —", EN: "— not selected —", ES: "— sin elegir —", IT: "— non scelto —", DE: "— nicht gewählt —", FR: "— non choisi —", ZH: "— 未选择 —"},
    "no_groups": {RU: "— нет групп —", EN: "— no groups —", ES: "— sin grupos —", IT: "— nessun gruppo —", DE: "— keine Gruppen —", FR: "— aucun groupe —", ZH: "— 没有班级 —"},
    "no_subjects": {RU: "— нет предметов —", EN: "— no subjects —", ES: "— sin asignaturas —", IT: "— nessuna materia —", DE: "— keine Fächer —", FR: "— aucune matière —", ZH: "— 没有科目 —"},
    "no_course_subjects": {
        RU: "— нет предметов у курса —",
        EN: "— year has no subjects —",
        ES: "— el curso no tiene asignaturas —",
        IT: "— l'anno non ha materie —",
        DE: "— Jahr hat keine Fächer —",
        FR: "— l'année n'a aucune matière —",
        ZH: "— 该年级没有科目 —",
    },

    "btn_del_sched": {RU: "🗑 Удалить выбранные занятия", EN: "🗑 Delete selected lessons", ES: "🗑 Eliminar clases", IT: "🗑 Elimina lezioni", DE: "🗑 Ausgewählte Stunden löschen", FR: "🗑 Supprimer les séances", ZH: "🗑 删除所选课程"},
    "btn_clear_sched": {RU: "Очистить всё расписание", EN: "Clear timetable", ES: "Borrar horario", IT: "Cancella orario", DE: "Stundenplan löschen", FR: "Effacer l'emploi du temps", ZH: "清空课程表"},
    "btn_to_table": {RU: "➡ В таблицу (7)", EN: "➡ To grid (7)", ES: "➡ A la tabla (7)", IT: "➡ Alla tabella (7)", DE: "➡ Zur Tabelle (7)", FR: "➡ Vers le tableau (7)", ZH: "➡ 转到表格 (7)"},
    "lbl_sched_table": {RU: "Расписание", EN: "Timetable", ES: "Horario", IT: "Orario", DE: "Stundenplan", FR: "Emploi du temps", ZH: "课程表"},
    "sched_hdr_subject": {RU: "Предмет", EN: "Subject", ES: "Asignatura", IT: "Materia", DE: "Fach", FR: "Matière", ZH: "科目"},
    "sched_hdr_kind": {RU: "Тип", EN: "Type", ES: "Tipo", IT: "Tipo", DE: "Typ", FR: "Type", ZH: "类型"},
    "sched_hdr_cell": {RU: "Ячейка", EN: "Slot", ES: "Casilla", IT: "Slot", DE: "Slot", FR: "Case", ZH: "时间段"},
    "sched_hdr_group": {RU: "Группа", EN: "Group", ES: "Grupo", IT: "Gruppo", DE: "Gruppe", FR: "Groupe", ZH: "班级"},
    "sched_hdr_aud": {RU: "Аудитория", EN: "Room", ES: "Aula", IT: "Aula", DE: "Raum", FR: "Salle", ZH: "教室"},
    "sched_hdr_day": {RU: "День", EN: "Day", ES: "Día", IT: "Giorno", DE: "Tag", FR: "Jour", ZH: "星期"},

    "cal_teacher": {RU: "Преподаватель:", EN: "Teacher:", ES: "Profesor:", IT: "Docente:", DE: "Lehrkraft:", FR: "Enseignant :", ZH: "教师："},

    "set_title": {RU: "Язык интерфейса", EN: "Interface language", ES: "Idioma de la interfaz", IT: "Lingua dell'interfaccia", DE: "Sprache der Oberfläche", FR: "Langue de l'interface", ZH: "界面语言"},
    "set_lang_label": {RU: "Язык:", EN: "Language:", ES: "Idioma:", IT: "Lingua:", DE: "Sprache:", FR: "Langue :", ZH: "语言："},
    "set_hint": {
        RU: "Выберите язык — весь интерфейс (вкладки, кнопки, таблицы, дни недели) переключится сразу. Выбор запоминается.",
        EN: "Pick a language — the whole interface (tabs, buttons, tables, weekdays) switches at once. Your choice is remembered.",
        ES: "Elija un idioma — toda la interfaz (pestañas, botones, tablas, días) cambiará a la vez. Su elección se guarda.",
        IT: "Scegli una lingua — l'intera interfaccia (schede, pulsanti, tabelle, giorni) cambia subito. La scelta viene ricordata.",
        DE: "Wählen Sie eine Sprache — die gesamte Oberfläche (Registerkarten, Schaltflächen, Tabellen, Wochentage) wechselt sofort. Ihre Wahl wird gespeichert.",
        FR: "Choisissez une langue — toute l'interface (onglets, boutons, tableaux, jours) change aussitôt. Votre choix est mémorisé.",
        ZH: "选择语言——整个界面（选项卡、按钮、表格、星期）将立即切换。您的选择会被记住。",
    },
    "set_done": {
        RU: "Язык применён.",
        EN: "Language applied.",
        ES: "Idioma aplicado.",
        IT: "Lingua applicata.",
        DE: "Sprache angewendet.",
        FR: "Langue appliquée.",
        ZH: "语言已应用。",
    },

    "weekday_0": {RU: "Пн", EN: "Mon", ES: "Lun", IT: "Lun", DE: "Mo", FR: "Lun", ZH: "周一"},
    "weekday_1": {RU: "Вт", EN: "Tue", ES: "Mar", IT: "Mar", DE: "Di", FR: "Mar", ZH: "周二"},
    "weekday_2": {RU: "Ср", EN: "Wed", ES: "Mié", IT: "Mer", DE: "Mi", FR: "Mer", ZH: "周三"},
    "weekday_3": {RU: "Чт", EN: "Thu", ES: "Jue", IT: "Gio", DE: "Do", FR: "Jeu", ZH: "周四"},
    "weekday_4": {RU: "Пт", EN: "Fri", ES: "Vie", IT: "Ven", DE: "Fr", FR: "Ven", ZH: "周五"},

    "course_fmt": {
        RU: "{n} курс",
        EN: "Year {n}",
        ES: "Curso {n}",
        IT: "Anno {n}",
        DE: "Jahr {n}",
        FR: "Année {n}",
        ZH: "第{n}学年",
    },
}


def tr(key: str) -> str:
    entry = TEXTS.get(key)
    if entry is None:
        return key
    return entry.get(_current, entry.get(RU, key))


def weekday_names() -> list[str]:
    return [tr(f"weekday_{i}") for i in range(5)]


def course_name(n: int) -> str:
    return tr("course_fmt").format(n=n)
