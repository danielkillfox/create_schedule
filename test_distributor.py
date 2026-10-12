

# test_distributor.py
# =====================================================================
# ПРОВЕРКИ раскладчика (тесты). Простыми словами:
# - Это "контрольные работы" для программы: мы придумываем маленькие примеры
#   (2 группы, 1 зал...) и проверяем, что раскладчик отвечает правильно.
# - Запуск: pytest  или  python -m pytest
# - Каждая функция test_* = одна проверка. Слово assert = "клянусь, что...".
#   Если клятва нарушена - тест краснеет и показывает, где ошибка.
# =====================================================================

from distributor import Group, Auditorium, distribute


def test_all_fit_in_one_aud():
    # Все влезают в один зал: группы 10 + 20 человек, зал на 30. Должны сесть оба, никого без места.
    groups = [Group(1, "A", 10), Group(2, "B", 20)]
    auds = [Auditorium(1, "A-101", 30)]
    r = distribute(groups, auds)
    assert len(r.placed) == 2
    assert r.not_placed == []


def test_some_not_fit():
    # Кто-то не влезает: группа B (70 чел) не помещается в зал на 60.
    # Значит, сядет только A, а B попадёт в список "не поместились".
    groups = [Group(1, "A", 50), Group(2, "B", 70)]
    auds = [Auditorium(1, "A-101", 60)]
    r = distribute(groups, auds)
    # A(50) влезает, B(70) не влезает ни в одну аудиторию
    assert len(r.placed) == 1
    assert len(r.not_placed) == 1
    assert r.not_placed[0].name == "B"


def test_empty():
    # Пустой вход = пустой выход. Проверяем, что программа не падает, если данных нет.
    r = distribute([], [])
    assert r.placed == []
    assert r.not_placed == []


def test_prefers_more_groups():
    """Оптимум: разместить больше групп, а не больше людей.

    Простыми словами: лучше посадить две маленькие группы, чем одну большую,
    даже если людей в сумме столько же. Проверяем, что обе группы сели по разным залам.
    """
    groups = [Group(1, "A", 15), Group(2, "B", 15)]
    auds = [Auditorium(1, "X", 20), Auditorium(2, "Y", 20)]
    r = distribute(groups, auds)
    # Обе группы должны поместиться — каждая в свою аудиторию
    assert len(r.placed) == 2
    assert r.total_people == 30


def test_whole_stream_one_room():
    """Лекция: весь поток вместе в одну аудиторию (best fit).

    Три группы по 10 = 30 человек. Есть залы на 20 и 30.
    Все должны сесть ВМЕСТЕ в большой зал (на 30) на 1-й паре.
    """
    groups = [Group(1, "A", 10), Group(2, "B", 10), Group(3, "C", 10)]
    auds = [Auditorium(1, "Small", 20), Auditorium(2, "Big", 30)]
    r = distribute(groups, auds, whole_stream=True)
    assert len(r.placed) == 3
    assert r.not_placed == []
    assert {p.auditorium.name for p in r.placed} == {"Big"}
    assert {p.cell for p in r.placed} == {1}


def test_whole_stream_no_room():
    """Лекция: нет зала на поток — все в not_placed + причина.

    Нужно 80 мест (40+40), а максимум есть 50. Значит, никто не сел,
    а в пояснении (note) написано, сколько мест не хватило (там есть число "80").
    """
    groups = [Group(1, "A", 40), Group(2, "B", 40)]
    auds = [Auditorium(1, "Small", 50)]
    r = distribute(groups, auds, whole_stream=True)
    assert len(r.placed) == 0
    assert len(r.not_placed) == 2
    assert "80" in r.note


def test_max_two_groups_per_room():
    """Практика: не больше 2 групп в одном кабинете в одной ячейке.

    5 групп по 10 человек, один огромный зал на 100.
    Без ограничения все влезли бы в одну пару, но правило "максимум 2"
    заставляет разбить их на несколько пар (в каждой паре не больше 2 групп).
    """
    groups = [Group(i, f"G{i}", 10) for i in range(1, 6)]
    auds = [Auditorium(1, "Lab", 100)]
    r = distribute(groups, auds, max_groups_per_room=2)
    assert len(r.placed) == 5
    from collections import Counter
    per_cell = Counter(p.cell for p in r.placed)
    assert all(v <= 2 for v in per_cell.values()), dict(per_cell)