# -*- coding: utf-8 -*-
"""Тесты модуля workouts."""
import pytest


@pytest.mark.usefixtures("patch_config")
def test_load_workouts():
    import workouts as wm
    list_w = wm.load_workouts()
    assert isinstance(list_w, list)
    assert len(list_w) >= 1
    w = list_w[0]
    assert "id" in w
    assert "title" in w
    assert "duration" in w
    assert "energy_level" in w or "type" in w


@pytest.mark.usefixtures("patch_config")
def test_pick_workout_returns_match():
    import workouts as wm
    # Ответы из опроса должны подобрать хотя бы одну тренировку
    w = wm.pick_workout("бодрячком", "овуляция", "15-20", "сила")
    assert w is not None
    assert "title" in w
    assert "link" in w
    assert "duration" in w


@pytest.mark.usefixtures("patch_config")
def test_pick_workout_fallback():
    import workouts as wm
    # Даже при неочевидных тегах должен вернуть что-то из списка (fallback)
    w = wm.pick_workout("уставшая", "перед месячными", "5-10", "подышать")
    assert w is not None


@pytest.mark.usefixtures("patch_config")
def test_get_by_category():
    import workouts as wm
    for cat in ["растяжка", "силовая", "дыхание", "экспресс"]:
        list_w = wm.get_by_category(cat)
        assert isinstance(list_w, list)
        for w in list_w:
            assert (w.get("type") or "").lower() == cat.lower()


@pytest.mark.usefixtures("patch_config")
def test_get_all_grouped_by_type():
    import workouts as wm
    by_type = wm.get_all_grouped_by_type()
    assert isinstance(by_type, dict)
    for t, workouts in by_type.items():
        assert isinstance(workouts, list)
        for w in workouts:
            assert (w.get("type") or "другое").lower() == t
