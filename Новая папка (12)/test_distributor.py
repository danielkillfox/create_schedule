

from distributor import Group, Auditorium, distribute


def test_all_fit_in_one_aud():
    groups = [Group(1, "A", 10), Group(2, "B", 20)]
    auds = [Auditorium(1, "A-101", 30)]
    r = distribute(groups, auds)
    assert len(r.placed) == 2
    assert r.not_placed == []


def test_some_not_fit():
    groups = [Group(1, "A", 50), Group(2, "B", 50)]
    auds = [Auditorium(1, "A-101", 60)]
    r = distribute(groups, auds)
    assert len(r.placed) == 1
    assert len(r.not_placed) == 1


def test_empty():
    r = distribute([], [])
    assert r.fill_percent == 0.0
    assert r.placed == []


def test_prefers_more_groups():
    """Оптимум: разместить больше групп, а не больше людей."""
    groups = [Group(1, "A", 15), Group(2, "B", 15)]
    auds = [Auditorium(1, "X", 20), Auditorium(2, "Y", 20)]
    r = distribute(groups, auds)
    # Обе группы должны поместиться — каждая в свою аудиторию
    assert len(r.placed) == 2
    assert r.total_people == 30