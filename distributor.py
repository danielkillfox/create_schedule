

# distributor.py - "УМНЫЙ РАСКЛАДЧИК".
# Простыми словами: рассаживает группы-студентов по аудиториям и парам,
# как пассажиров по автобусам и рейсам. Лекция = все вместе в одном зале,
# практика = делим по кабинетам (не больше 2 групп в кабинете).
from dataclasses import dataclass, field
from typing import Optional
import time






#  МОДЕЛИ - карточки данных (что мы знаем про каждый объект)


@dataclass
class Group:
    # Группа: номер, название ("ИСП-101"), число студентов.
    id: int
    name: str
    students: int

    def __post_init__(self):
        # Проверка: группа не может быть пустой.
        if self.students <= 0:
            raise ValueError(f"Группа {self.name}: студентов должно быть > 0")


@dataclass
class Auditorium:
    # Аудитория: номер, название, число мест, тип ("lecture"=лекционный зал, "practice"=кабинет).
    id: int
    name: str
    capacity: int
    kind: str = "lecture"

    def __post_init__(self):
        # Проверяем: мест > 0 и тип только из двух разрешённых.
        if self.capacity <= 0:
            raise ValueError(f"Аудитория {self.name}: вместимость должна быть > 0")
        if self.kind not in ("lecture", "practice"):
            raise ValueError(f"Аудитория {self.name}: неизвестный тип {self.kind!r}")


@dataclass
class PlacedGroup:
    # "Группа уже посажена": кто + куда + на какую пару + в какой день (0=Пн..4=Пт).
    group: Group
    auditorium: Auditorium
    cell: int     # номер ячейки (1..MAX_CELLS)
    weekday: int = 0  # день недели 0=Пн..4=Пт (назначает планировщик вкладки 5)


@dataclass
class DistributionResult:
    # Итог раскладки: кого посадили (placed), кого не смогли (not_placed), пояснение (note).
    placed: list[PlacedGroup] = field(default_factory=list)
    not_placed: list[Group] = field(default_factory=list)
    auditoriums: list[Auditorium] = field(default_factory=list)
    note: str = ""  # пояснение, если разместить не удалось (например, нет зала на поток)

    @property
    def total_people(self) -> int:
        # Сколько всего человек удалось рассадить.
        return sum(p.group.students for p in self.placed)

    @property
    def cells_used(self) -> int:
        # Сколько пар понадобилось (максимальный номер занятой пары).
        return max((p.cell for p in self.placed), default=0)

    def by_cell(self) -> dict[int, list[PlacedGroup]]:
        # Разложить по парам: {1: [кто на 1 паре], 2: [...]}.
        d: dict[int, list[PlacedGroup]] = {}
        for p in self.placed:
            d.setdefault(p.cell, []).append(p)
        return d

    def cells(self) -> dict[tuple[int, int], list[PlacedGroup]]:
        # Разложить по (пара + зал): {(1, id_зала): [группы]}. Удобно для отчёта.
        d: dict[tuple[int, int], list[PlacedGroup]] = {}
        for p in self.placed:
            d.setdefault((p.cell, p.auditorium.id), []).append(p)
        return d



#  ЯДРО: БИН-ПАКОВКА НА КАЖДУЮ ЯЧЕЙКУ ("распихать вещи по коробкам")


def distribute(
    groups: list[Group],
    auditoriums: list[Auditorium],
    time_per_cell: float = 1.0,
    max_groups_per_room: Optional[int] = None,
    whole_stream: bool = False,
) -> DistributionResult:
    """Размещает группы по аудиториям и ячейкам (парам).

    Простыми словами:
    - groups: кого сажаем (список групп).
    - auditoriums: куда сажаем (список залов).
    - whole_stream=True (лекции): весь поток идёт вместе в одну аудиторию —
    выбирается наименьшая, куда влезают все. Не влезли — все в not_placed.
    - max_groups_per_room (практики): не больше N групп в одной аудитории
    в одной ячейке (вместимость при этом тоже соблюдается).
    - time_per_cell: сколько секунд думать над одной парой (чтобы не зависнуть).
    Возвращает коробку DistributionResult: кого посадили + кого не смогли.
    """

    # Если сажать некого или некуда - сразу возвращаем "никого не посадили".
    if not groups or not auditoriums:
        return DistributionResult(
            not_placed=list(groups),
            auditoriums=list(auditoriums),
        )

    # Режим лекции: весь поток вместе.
    if whole_stream:
        return _distribute_whole_stream(groups, auditoriums)

    # Режим практики: заполняем пару за парой.
    # Берём оставшихся, пакуем одну пару, тех кто не влез - несём на следующую пару. И так по кругу.
    remaining = list(groups)
    all_placed: list[PlacedGroup] = []
    cell = 1

    while remaining:
        placed_now, remaining = _pack_one_cell(
            remaining, auditoriums, cell, time_per_cell,
            max_groups_per_room=max_groups_per_room,
        )
        if not placed_now:
            break  # в эту пару уже никого нельзя впихнуть - дальше бессмысленно
        all_placed.extend(placed_now)
        cell += 1  # переходим к следующей паре

    return DistributionResult(
        placed=all_placed,
        not_placed=remaining,
        auditoriums=list(auditoriums),
    )


def _distribute_whole_stream(
    groups: list[Group],
    auditoriums: list[Auditorium],
) -> DistributionResult:
    """Лекция: весь поток в одну аудиторию (best fit = берём самый маленький подходящий зал, чтобы большой не занимать зря)."""
    total = sum(g.students for g in groups)  # сколько всего человек на потоке
    fitting = [a for a in auditoriums if a.capacity >= total]  # залы, куда поток влезает
    if not fitting:
        # Нет зала: всех записываем в "не поместились" и объясняем почему (сколько надо / сколько максимум есть).
        biggest = max(a.capacity for a in auditoriums)
        return DistributionResult(
            not_placed=list(groups),
            auditoriums=list(auditoriums),
            note=(f"Нет аудитории на весь поток: нужно мест {total}, "
                  f"максимум {biggest}."),
        )
    # Из подходящих берём самый тесный (экономим большие залы). При равенстве - по алфавиту.
    best = min(fitting, key=lambda a: (a.capacity, a.name))
    return DistributionResult(
        placed=[PlacedGroup(group=g, auditorium=best, cell=1) for g in groups],
        auditoriums=list(auditoriums),
    )

def _pack_one_cell(
    groups: list[Group],
    auditoriums: list[Auditorium],
    cell: int,
    time_limit: float,
    max_groups_per_room: Optional[int] = None,
) -> tuple[list[PlacedGroup], list[Group]]:
    # Упаковывает ОДНУ пару (ячейку): решает, кто в какой зал сядет именно на этой паре.
    # Как работает (игра "Тетрис наоборот"):
    # - сначала сортируем группы от самой большой к маленькой (больших сажать труднее, им - первыми),
    # - потом перебираем варианты "а что если эту группу сюда, а эту туда" (метод перебора backtrack),
    # - цель: посадить КАК МОЖНО БОЛЬШЕ ГРУПП, используя КАК МОЖНО МЕНЬШЕ залов.
    # Возвращает два списка: (кого посадили на эту пару, кто остался на следующие пары).
    n = len(groups)
    caps = [a.capacity for a in auditoriums]  # вместимость каждого зала
    loads = [0] * len(caps)  # сколько мест уже занято в каждом зале (пока нули)
    counts = [0] * len(caps)  # сколько групп уже сидит в каждом зале
    assign: list[Optional[int]] = [None] * n  # черновик: группа №i -> зал №c (пока пусто)
    order = sorted(range(n), key=lambda i: -groups[i].students)  # порядок: большие группы первыми

    best = {"score": (-1, 0, -1), "assign": [None] * n}  # лучший найденный вариант (пока никакой)
    deadline = time.monotonic() + time_limit  # время, когда надо перестать думать (чтобы не висеть)

    def backtrack(k: int, placed_count: int, placed_people: int, bins_used: int) -> None:
        # Рекурсивный перебор: k = какую по счёту группу сейчас сажаем.
        # placed_count = скольких уже посадили, placed_people = сколько человек посадили,
        # bins_used = сколько залов задействовали.
        if time.monotonic() > deadline:
            return  # время вышло - перестаём перебирать
        if placed_count + (n - k) < best["score"][0]:
            return  # даже в идеале уже не обгоним лучший результат - ветку бросаем

        # Оценка варианта: (больше групп = лучше, меньше залов = лучше, больше людей = лучше).
        score = (placed_count, -bins_used, placed_people)
        if score > best["score"]:
            best["score"] = score
            best["assign"] = assign[:]  # запоминаем как лучший

        if k == n:
            return  # все группы рассмотрели - конец ветки

        idx = order[k]  # берём очередную (начиная с больших) группу
        size = groups[idx].students  # сколько в ней человек

        tried = set()  # чтобы не пробовать одинаковые залы дважды (ускорение)
        for c in range(len(caps)):
            # Пропускаем зал, если в нём уже сидит максимум групп (например, 2 для практики).
            if max_groups_per_room is not None and counts[c] >= max_groups_per_room:
                continue
            # Сажаем только если влезает по местам.
            if loads[c] + size <= caps[c] and (loads[c], counts[c]) not in tried:
                tried.add((loads[c], counts[c]))
                new_bin = (loads[c] == 0)  # зал был пустой? значит, открываем новый зал
                loads[c] += size  # "сажаем": занимаем места
                counts[c] += 1  # и увеличиваем счётчик групп
                assign[idx] = c  # записываем в черновик
                backtrack(  # идём сажать следующую группу
                    k + 1,
                    placed_count + 1,
                    placed_people + size,
                    bins_used + (1 if new_bin else 0),
                )
                # Откат ("а что если не сюда?"): убираем группу обратно и пробуем другой зал.
                loads[c] -= size
                counts[c] -= 1
                assign[idx] = None

        # Вариант "эту группу вообще не сажаем на эту пару" (оставляем на следующую).
        backtrack(k + 1, placed_count, placed_people, bins_used)

    backtrack(0, 0, 0, 0)  # запускаем перебор с первой группы

    placed: list[PlacedGroup] = []
    not_placed: list[Group] = []
    for i, g in enumerate(groups):
        c = best["assign"][i]
        if c is None:
            not_placed.append(g)
        else:
            placed.append(PlacedGroup(group=g, auditorium=auditoriums[c], cell=cell))
    return placed, not_placed