# -*- coding: utf-8 -*-
"""Тесты модуля database."""
import json
from datetime import date

import pytest


@pytest.mark.usefixtures("patch_config")
def test_init_db_and_create_user(db):
    db.init_db()
    db.create_user(999)
    u = db.get_user(999)
    assert u is not None
    assert u["user_id"] == 999
    assert u["streak_days"] == 0
    assert u["max_streak"] == 0
    assert u["freezes_left"] == 3
    assert u["freezes_used"] == 0
    assert u["onboarding_done"] == 0
    assert u["goals"] == []
    assert u["achievements"] == []


@pytest.mark.usefixtures("patch_config")
def test_update_user(db):
    db.init_db()
    db.create_user(100)
    db.update_user(100, name="Тест", age="25-30", onboarding_done=1)
    u = db.get_user(100)
    assert u["name"] == "Тест"
    assert u["age"] == "25-30"
    assert u["onboarding_done"] == 1


@pytest.mark.usefixtures("patch_config")
def test_set_and_get_user_state(db):
    db.init_db()
    db.create_user(101)
    db.set_user_state(101, "survey_energy", "бодрячком")
    state, data = db.get_user_state(101)
    assert state == "survey_energy"
    assert data == "бодрячком"


@pytest.mark.usefixtures("patch_config")
def test_record_workout_done(db):
    db.init_db()
    db.create_user(102)
    res = db.record_workout_done(102)
    assert res["streak_days"] == 1
    assert res["max_streak"] == 1
    assert res["new_achievement"] == "Первый шаг"
    u = db.get_user(102)
    assert u["achievements"] == ["Первый шаг"]
    assert u["monthly_count"] == 1
    res2 = db.record_workout_done(102)
    assert res2["streak_days"] == 2
    assert res2["new_achievement"] is None


@pytest.mark.usefixtures("patch_config")
def test_use_freeze(db):
    db.init_db()
    db.create_user(103)
    assert db.use_freeze(103) is True
    u = db.get_user(103)
    assert u["freezes_left"] == 2
    assert u["freezes_used"] == 1
    db.use_freeze(103)
    db.use_freeze(103)
    assert db.use_freeze(103) is False
    u = db.get_user(103)
    assert u["freezes_left"] == 0


@pytest.mark.usefixtures("patch_config")
def test_reset_streak(db):
    db.init_db()
    db.create_user(104)
    db.record_workout_done(104)
    db.reset_streak(104)
    u = db.get_user(104)
    assert u["streak_days"] == 0


@pytest.mark.usefixtures("patch_config")
def test_survey_and_workout_done_today(db):
    db.init_db()
    db.create_user(105)
    today = date.today().isoformat()
    assert db.workout_done_today(105) is False
    db.save_survey(105, "бодрячком", "овуляция", "15-20", "сила", "str_003")
    db.set_survey_completed(105, "супер")
    assert db.workout_done_today(105) is True


@pytest.mark.usefixtures("patch_config")
def test_add_coach_question(db):
    db.init_db()
    db.create_user(106)
    db.add_coach_question(106, "Как часто заниматься?")
    # Проверяем через соединение, что запись есть
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM coach_questions WHERE user_id = 106").fetchone()
    conn.close()
    assert row is not None
    assert row["text"] == "Как часто заниматься?"


@pytest.mark.usefixtures("patch_config")
def test_get_users_for_reminder(db):
    db.init_db()
    db.create_user(107)
    db.update_user(107, reminder_time="утро", is_active=1)
    db.create_user(108)
    db.update_user(108, reminder_time="утро", is_active=1)
    db.create_user(109)
    db.update_user(109, reminder_time="день", is_active=1)
    ids = db.get_users_for_reminder("утро")
    assert 107 in ids
    assert 108 in ids
    assert 109 not in ids


@pytest.mark.usefixtures("patch_config")
def test_reset_all_monthly(db):
    db.init_db()
    db.create_user(110)
    db.update_user(110, freezes_left=0, freezes_used=3, monthly_count=24)
    db.reset_all_monthly()
    u = db.get_user(110)
    assert u["freezes_left"] == 3
    assert u["freezes_used"] == 0
    assert u["monthly_count"] == 0


@pytest.mark.usefixtures("patch_config")
def test_user_count(db):
    db.init_db()
    db.create_user(201)
    db.create_user(202)
    assert db.user_count() == 2
