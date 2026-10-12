

from distributor import Group, Auditorium, distribute


def test_all_fit_in_one_aud():
    groups = [Group(1, "A", 10), Group(2, "B", 20)]
    auds = [Auditorium(1, "A-101", 30)]
    r = distribute(groups, auds)
    assert len(r.placed) == 2
    assert r.not_placed == []


def test_some_not_fit():
    groups = [Group(1, "A", 50), Group(2, "B", 70)]
    auds = [Auditorium(1, "A-101", 60)]
    r = distribute(groups, auds)
    assert len(r.placed) == 1
    assert len(r.not_placed) == 1
    assert r.not_placed[0].name == "B"


def test_empty():
    r = distribute([], [])
    assert r.placed == []
    assert r.not_placed == []


def test_prefers_more_groups():
    groups = [Group(1, "A", 15), Group(2, "B", 15)]
    auds = [Auditorium(1, "X", 20), Auditorium(2, "Y", 20)]
    r = distribute(groups, auds)
    assert len(r.placed) == 2
    assert r.total_people == 30


def test_whole_stream_one_room():
    groups = [Group(1, "A", 10), Group(2, "B", 10), Group(3, "C", 10)]
    auds = [Auditorium(1, "Small", 20), Auditorium(2, "Big", 30)]
    r = distribute(groups, auds, whole_stream=True)
    assert len(r.placed) == 3
    assert r.not_placed == []
    assert {p.auditorium.name for p in r.placed} == {"Big"}
    assert {p.cell for p in r.placed} == {1}


def test_whole_stream_no_room():
    groups = [Group(1, "A", 40), Group(2, "B", 40)]
    auds = [Auditorium(1, "Small", 50)]
    r = distribute(groups, auds, whole_stream=True)
    assert len(r.placed) == 0
    assert len(r.not_placed) == 2
    assert "80" in r.note


def test_max_two_groups_per_room():
    groups = [Group(i, f"G{i}", 10) for i in range(1, 6)]
    auds = [Auditorium(1, "Lab", 100)]
    r = distribute(groups, auds, max_groups_per_room=2)
    assert len(r.placed) == 5
    from collections import Counter
    per_cell = Counter(p.cell for p in r.placed)
    assert all(v <= 2 for v in per_cell.values()), dict(per_cell)