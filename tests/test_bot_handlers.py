# -*- coding: utf-8 -*-
"""Тесты обработчиков бота (с моками Telegram Update/Context)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

# Чтобы импорт bot не тянул .env и не падал без токена
@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_123")


def make_message_mock():
    msg = MagicMock()
    msg.reply_text = AsyncMock(return_value=None)
    msg.text = None
    return msg


def make_update_message(user_id=12345, text=""):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.full_name = "Test User"
    update.effective_message = make_message_mock()
    update.message = update.effective_message
    update.message.text = text
    update.callback_query = None
    return update


def make_callback_query(data, message=None):
    q = MagicMock()
    q.data = data
    q.answer = AsyncMock(return_value=None)
    q.edit_message_text = AsyncMock(return_value=None)
    if message is None:
        message = make_message_mock()
    q.message = message
    q.message.reply_text = AsyncMock(return_value=None)
    return q


def make_context():
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock(return_value=None)
    return context


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_start_new_user(db):
    import bot
    db.init_db()
    update = make_update_message(99901)
    context = make_context()
    await bot.start(update, context)
    assert update.effective_message.reply_text.called
    call_args = update.effective_message.reply_text.call_args
    assert "Привет" in call_args[0][0] or "красотка" in call_args[0][0]
    u = db.get_user(99901)
    assert u is not None
    assert u["onboarding_done"] == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_start_after_onboarding(db):
    import bot
    db.init_db()
    db.create_user(99902)
    db.update_user(99902, onboarding_done=1, name="Маша")
    update = make_update_message(99902)
    context = make_context()
    await bot.start(update, context)
    assert update.effective_message.reply_text.called
    call_args = update.effective_message.reply_text.call_args
    assert "Главное меню" in call_args[0][0]


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_stop_cmd(db):
    import bot
    db.init_db()
    db.create_user(99903)
    db.update_user(99903, is_active=1, reminder_time="утро")
    update = make_update_message(99903)
    context = make_context()
    await bot.stop_cmd(update, context)
    u = db.get_user(99903)
    assert u["is_active"] == 0
    assert u["reminder_time"] is None
    assert update.effective_message.reply_text.called


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_onboarding_callback_about(db):
    import bot
    db.init_db()
    db.create_user(99904)
    update = make_update_message(99904)
    update.callback_query = make_callback_query("onb_about")
    context = make_context()
    await bot.handle_callback_query(update, context)
    assert update.callback_query.edit_message_text.called
    state, _ = db.get_user_state(99904)
    assert state == "onb_name"


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_onboarding_callback_age(db):
    import bot
    db.init_db()
    db.create_user(99905)
    db.set_user_state(99905, "onb_age", "")
    update = make_update_message(99905)
    update.callback_query = make_callback_query("age_25-30")
    context = make_context()
    await bot.handle_callback_query(update, context)
    u = db.get_user(99905)
    assert u["age"] == "25-30"
    state, data = db.get_user_state(99905)
    assert state == "onb_goals"


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_onboarding_callback_goal_done(db):
    import json
    import bot
    import messages as msg
    db.init_db()
    db.create_user(99906)
    db.update_user(99906, name="Anya", age="30-35")
    selected_goal = msg.GOALS_OPTIONS[0]
    db.set_user_state(99906, "onb_goals", json.dumps([selected_goal], ensure_ascii=False))
    update = make_update_message(99906)
    update.callback_query = make_callback_query("goal_done")
    context = make_context()
    await bot.handle_callback_query(update, context)
    u = db.get_user(99906)
    assert u["onboarding_done"] == 1
    assert u.get("name") == "Anya"
    assert selected_goal in (u.get("goals") or [])


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_onboarding_message_name(db):
    import bot
    db.init_db()
    db.create_user(99907)
    db.set_user_state(99907, "onb_name", "")
    update = make_update_message(99907, text="Катя")
    context = make_context()
    await bot.handle_text_message(update, context)
    u = db.get_user(99907)
    assert u["name"] == "Катя"
    state, _ = db.get_user_state(99907)
    assert state == "onb_age"


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_main_menu_training_today(db):
    import bot
    db.init_db()
    db.create_user(99908)
    db.update_user(99908, onboarding_done=1)
    update = make_update_message(99908, text="🔥 Тренировка на сегодня")
    context = make_context()
    await bot.handle_text_message(update, context)
    assert update.message.reply_text.called
    state, _ = db.get_user_state(99908)
    assert state == "survey_energy"


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_main_menu_progress(db):
    import bot
    db.init_db()
    db.create_user(99909)
    db.update_user(99909, onboarding_done=1, streak_days=5, max_streak=5, monthly_count=3, freezes_left=2)
    update = make_update_message(99909, text="🔥 Мой прогресс")
    context = make_context()
    await bot.handle_text_message(update, context)
    assert update.message.reply_text.called
    text = update.message.reply_text.call_args[0][0]
    assert "5" in text
    assert "прогресс" in text.lower() or "серия" in text.lower()


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_survey_flow_energy_cycle_time_goal(db):
    import bot
    db.init_db()
    db.create_user(99910)
    db.update_user(99910, onboarding_done=1, name="Таня")
    context = make_context()

    update = make_update_message(99910)
    update.callback_query = make_callback_query("survey_energy_бодрячком")
    await bot.handle_callback_query(update, context)
    state, data = db.get_user_state(99910)
    assert state == "survey_cycle"

    update.callback_query = make_callback_query("survey_cycle_овуляция")
    await bot.handle_callback_query(update, context)
    state, data = db.get_user_state(99910)
    assert state == "survey_time"
    assert "бодрячком" in (data or "")
    assert "овуляция" in (data or "")

    update.callback_query = make_callback_query("survey_time_15-20")
    await bot.handle_callback_query(update, context)
    state, data = db.get_user_state(99910)
    assert state == "survey_goal"

    update.callback_query = make_callback_query("survey_goal_сила")
    await bot.handle_callback_query(update, context)
    state, _ = db.get_user_state(99910)
    assert state == ""
    # Должна быть выдача тренировки и главное меню
    assert update.callback_query.edit_message_text.called
    edit_text = update.callback_query.edit_message_text.call_args[0][0]
    assert "Таня" in edit_text or "тренировк" in edit_text.lower()


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_reaction_super_records_workout(db):
    import bot
    db.init_db()
    db.create_user(99911)
    db.update_user(99911, name="Оля")
    today = __import__("datetime").date.today().isoformat()
    conn = db.get_connection()
    conn.execute(
        """INSERT INTO survey_answers (user_id, survey_date, energy, cycle_phase, time_slot, goal, created_at)
           VALUES (99911, ?, 'бодрячком', 'овуляция', '15-20', 'сила', datetime('now'))""",
        (today,),
    )
    conn.commit()
    conn.close()

    update = make_update_message(99911)
    update.callback_query = make_callback_query("reaction_супер")
    context = make_context()
    await bot.handle_callback_query(update, context)

    u = db.get_user(99911)
    assert u["streak_days"] == 1
    assert "Первый шаг" in (u.get("achievements") or [])
    assert db.workout_done_today(99911)


@pytest.mark.asyncio
@pytest.mark.usefixtures("patch_config")
async def test_get_next_achievement():
    import bot
    assert bot.get_next_achievement(0) == ("Первый шаг", 1)
    assert bot.get_next_achievement(2) == ("Огонёк зажёгся", 1)
    assert bot.get_next_achievement(7) == ("Привычка закрепляется", 7)
    assert bot.get_next_achievement(90)[0] == "Богиня регулярности"
