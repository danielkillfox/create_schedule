

from dataclasses import dataclass, field
from typing import Optional
import time






#  МОДЕЛИ


@dataclass
class Group:
    id: int
    name: str
    students: int

    def __post_init__(self):
        if self.students <= 0:
            raise ValueError(f"Группа {self.name}: студентов должно быть > 0")


@dataclass
class Auditorium:
    id: int
    name: str
    capacity: int
    kind: str = "lecture"

    def __post_init__(self):
        if self.capacity <= 0:
            raise ValueError(f"Аудитория {self.name}: вместимость должна быть > 0")
        if self.kind not in ("lecture", "practice"):
            raise ValueError(f"Аудитория {self.name}: неизвестный тип {self.kind!r}")


@dataclass
class PlacedGroup:
    group: Group
    auditorium: Auditorium
    cell: int     # номер ячейки (1..MAX_CELLS)


@dataclass
class DistributionResult:
    placed: list[PlacedGroup] = field(default_factory=list)
    not_placed: list[Group] = field(default_factory=list)
    auditoriums: list[Auditorium] = field(default_factory=list)

    @property
    def total_people(self) -> int:
        return sum(p.group.students for p in self.placed)

    @property
    def cells_used(self) -> int:
        return max((p.cell for p in self.placed), default=0)

    def by_cell(self) -> dict[int, list[PlacedGroup]]:
        d: dict[int, list[PlacedGroup]] = {}
        for p in self.placed:
            d.setdefault(p.cell, []).append(p)
        return d

    def cells(self) -> dict[tuple[int, int], list[PlacedGroup]]:
        d: dict[tuple[int, int], list[PlacedGroup]] = {}
        for p in self.placed:
            d.setdefault((p.cell, p.auditorium.id), []).append(p)
        return d



#  ЯДРО: БИН-ПАКОВКА НА КАЖДУЮ ЯЧЕЙКУ


def distribute(
    groups: list[Group],
    auditoriums: list[Auditorium],
    time_per_cell: float = 1.0,
) -> DistributionResult:

    if not groups or not auditoriums:
        return DistributionResult(
            not_placed=list(groups),
            auditoriums=list(auditoriums),
        )

    remaining = list(groups)
    all_placed: list[PlacedGroup] = []
    cell = 1

    while remaining:
        placed_now, remaining = _pack_one_cell(
            remaining, auditoriums, cell, time_per_cell
        )
        if not placed_now:
            break
        all_placed.extend(placed_now)
        cell += 1

    return DistributionResult(
        placed=all_placed,
        not_placed=remaining,
        auditoriums=list(auditoriums),
    )

def _pack_one_cell(
    groups: list[Group],
    auditoriums: list[Auditorium],
    cell: int,
    time_limit: float,
) -> tuple[list[PlacedGroup], list[Group]]:
    n = len(groups)
    caps = [a.capacity for a in auditoriums]
    loads = [0] * len(caps)
    assign: list[Optional[int]] = [None] * n
    order = sorted(range(n), key=lambda i: -groups[i].students)

    best = {"score": (-1, 0, -1), "assign": [None] * n}
    deadline = time.monotonic() + time_limit

    def backtrack(k: int, placed_count: int, placed_people: int, bins_used: int) -> None:
        if time.monotonic() > deadline:
            return
        if placed_count + (n - k) < best["score"][0]:
            return

        score = (placed_count, -bins_used, placed_people)
        if score > best["score"]:
            best["score"] = score
            best["assign"] = assign[:]

        if k == n:
            return

        idx = order[k]
        size = groups[idx].students

        tried = set()
        for c in range(len(caps)):
            if loads[c] + size <= caps[c] and loads[c] not in tried:
                tried.add(loads[c])
                new_bin = (loads[c] == 0)
                loads[c] += size
                assign[idx] = c
                backtrack(
                    k + 1,
                    placed_count + 1,
                    placed_people + size,
                    bins_used + (1 if new_bin else 0),
                )
                loads[c] -= size
                assign[idx] = None

        backtrack(k + 1, placed_count, placed_people, bins_used)

    backtrack(0, 0, 0, 0)

    placed: list[PlacedGroup] = []
    not_placed: list[Group] = []
    for i, g in enumerate(groups):
        c = best["assign"][i]
        if c is None:
            not_placed.append(g)
        else:
            placed.append(PlacedGroup(group=g, auditorium=auditoriums[c], cell=cell))
    return placed, not_placed