# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import List, Optional

import config


def load_workouts() -> List[dict]:
    path = config.WORKOUTS_JSON
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def pick_workout(energy: str, cycle: str, time_slot: str, goal: str) -> Optional[dict]:
    """Подбор тренировки по ответам опроса. Возвращает первую подходящую или с макс. совпадениями."""
    workouts = load_workouts()
    if not workouts:
        return None

    # Нормализуем значения под теги в JSON
    energy_map = {"бодрячком": "бодрячком", "спокойное": "спокойное", "уставшая": "уставшая", "стресс": "стресс"}
    cycle_map = {
        "месячные": "месячные",
        "после месячных": "после месячных",
        "овуляция": "овуляция",
        "перед месячными": "перед месячными",
        "не отслеживаю": "не отслеживаю",
    }
    goal_map = {"сила": "сила", "потянуться": "потянуться", "подвигаться": "подвигаться", "подышать": "подышать"}

    energy_n = energy_map.get(energy, energy)
    cycle_n = cycle_map.get(cycle, cycle)
    goal_n = goal_map.get(goal, goal)

    best = None
    best_score = -1

    for w in workouts:
        el = w.get("energy_level") or []
        if not isinstance(el, list):
            el = [el]
        cp = w.get("cycle_phase") or []
        if not isinstance(cp, list):
            cp = [cp]
        ts = w.get("time_slot") or []
        if not isinstance(ts, list):
            ts = [ts]
        gl = w.get("goal") or []
        if not isinstance(gl, list):
            gl = [gl]

        score = 0
        if energy_n in el:
            score += 2
        if cycle_n in cp:
            score += 2
        if time_slot in ts:
            score += 2
        if goal_n in gl:
            score += 2

        if score > best_score:
            best_score = score
            best = w

    return best if best_score >= 2 else (workouts[0] if workouts else None)


def get_by_category(category: str) -> List[dict]:
    """Категория: силовая, растяжка, дыхание, экспресс."""
    workouts = load_workouts()
    return [w for w in workouts if (w.get("type") or "").lower() == category.lower()]


def get_all_grouped_by_type() -> dict:
    workouts = load_workouts()
    by_type = {}
    for w in workouts:
        t = (w.get("type") or "другое").lower()
        by_type.setdefault(t, []).append(w)
    return by_type
