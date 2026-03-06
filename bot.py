# -*- coding: utf-8 -*-
"""
Telegram-бот «Тело говорит» — клуб бережных тренировок.
Реализация по ТЗ: онбординг, опрос, подбор тренировок, мотивация, прогресс, напоминания.
"""
from pathlib import Path
_env = Path(__file__).resolve().parent / ".env"
if _env.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env)
    except ImportError:
        pass

import json
import logging
from datetime import date, datetime, time as dtime
from typing import Optional

from telegram import Update
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

import config
import database as db
from telegram.ext import Defaults
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Moscow")
except ImportError:
    TZ = None  # Python < 3.9
import messages as msg
import keyboards as kb
import workouts as wm

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ——— Достижения по порогам (для текста «следующая цель») ———
ACHIEVEMENT_THRESHOLDS = [
    (1, "Первый шаг"),
    (3, "Огонёк зажёгся"),
    (7, "На связи с телом"),
    (14, "Привычка закрепляется"),
    (30, "Мастерица бережности"),
    (60, "Нереально крутая"),
    (90, "Богиня регулярности"),
]


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок: Conflict = два экземпляра бота, остальное — логируем."""
    err = context.error
    if isinstance(err, Conflict):
        logger.error(
            "Ошибка Conflict: уже запущен другой экземпляр бота с этим токеном. "
            "Останови все другие окна/терминалы с «python bot.py» (Ctrl+C) и запусти бота заново в одном месте."
        )
        return
    logger.exception("Ошибка при обработке обновления: %s", err)


def get_next_achievement(streak_days: int) -> tuple:
    """Возвращает (название, сколько дней осталось)."""
    for days, name in ACHIEVEMENT_THRESHOLDS:
        if streak_days < days:
            return name, days - streak_days
    return "Богиня регулярности", 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.create_user(user_id)
    user = db.get_user(user_id)

    if user and user.get("onboarding_done"):
        await update.effective_message.reply_text(
            msg.MAIN_MENU_TITLE,
            reply_markup=kb.main_menu_keyboard(),
        )
        return

    await update.effective_message.reply_text(
        msg.WELCOME,
        reply_markup=kb.welcome_keyboard(),
    )


async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.update_user(update.effective_user.id, is_active=0, reminder_time=None)
    await update.effective_message.reply_text(msg.STOPPED)


# ——— Один обработчик всех callback-кнопок (опрос + онбординг + заморозки + напоминания + библиотека) ———
# В PTB при одном фильтре вызывается только первый обработчик. onboarding_callback раньше
# «съедал» все callback (в т.ч. survey_energy_*), и survey_callback не вызывался.
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data

    # ——— Опрос (survey_*, reaction_*, start_survey) — приоритет, чтобы кнопки опроса работали ———
    if data == "start_survey":
        db.set_user_state(user_id, "survey_energy", "")
        await query.edit_message_text(msg.Q_ENERGY, reply_markup=kb.energy_keyboard())
        return

    if data.startswith("survey_energy_"):
        energy = data.replace("survey_energy_", "")
        db.set_user_state(user_id, "survey_cycle", energy)
        await query.edit_message_text(msg.Q_CYCLE, reply_markup=kb.cycle_keyboard())
        return

    if data.startswith("survey_cycle_"):
        cycle = data.replace("survey_cycle_", "")
        _, state_data = db.get_user_state(user_id)
        db.set_user_state(user_id, "survey_time", f"{state_data or ''}|{cycle}")
        await query.edit_message_text(msg.Q_TIME, reply_markup=kb.time_keyboard())
        return

    if data.startswith("survey_time_"):
        time_slot = data.replace("survey_time_", "")
        _, state_data = db.get_user_state(user_id)
        parts = (state_data or "").split("|")
        energy = parts[0] if parts else ""
        cycle = parts[1] if len(parts) > 1 else ""
        db.set_user_state(user_id, "survey_goal", f"{energy}|{cycle}|{time_slot}")
        await query.edit_message_text(msg.Q_GOAL_TODAY, reply_markup=kb.goal_today_keyboard())
        return

    if data.startswith("survey_goal_"):
        goal = data.replace("survey_goal_", "")
        _, state_data = db.get_user_state(user_id)
        parts = (state_data or "").split("|")
        energy = parts[0] if parts else ""
        cycle = parts[1] if len(parts) > 1 else ""
        time_slot = parts[2] if len(parts) > 2 else ""
        workout = wm.pick_workout(energy, cycle, time_slot, goal)
        db.save_survey(user_id, energy, cycle, time_slot, goal, workout.get("id") if workout else None)
        db.set_user_state(user_id, "", "")

        user = db.get_user(user_id)
        name = user.get("name") or "красотка"
        if workout:
            w_text = msg.WORKOUT_PICK.format(
                name=name,
                title=workout.get("title", "Тренировка"),
                duration=workout.get("duration", 15),
                equipment=workout.get("equipment", "коврик"),
            )
            link = workout.get("link") or "https://example.com"
            await query.edit_message_text(w_text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.workout_start_keyboard(link))
            await query.message.reply_text(msg.HOW_WAS_WORKOUT, reply_markup=kb.reaction_keyboard())
        else:
            await query.edit_message_text("Подходящую тренировку пока не подобрала — загляни в 📚 Библиотеку тренировок 🫶")
        await query.message.reply_text(msg.MAIN_MENU_TITLE, reply_markup=kb.main_menu_keyboard())
        return

    if data.startswith("reaction_"):
        reaction = data.replace("reaction_", "")
        already_done = db.workout_done_today(user_id)
        db.set_survey_completed(user_id, reaction)
        if reaction != "слилась" and not already_done:
            res = db.record_workout_done(user_id)
        else:
            res = {}
        user = db.get_user(user_id)
        streak = res.get("streak_days") or user.get("streak_days") or 0
        freezes_left = user.get("freezes_left") or 0
        next_name, days_to_next = get_next_achievement(streak)

        if reaction == "слилась":
            await query.edit_message_text(msg.WHAT_STOPPED)
            db.set_user_state(user_id, "what_stopped", "")
            return

        if res.get("new_achievement"):
            ach = res["new_achievement"]
            m = msg.ACHIEVEMENT_MESSAGES.get(ach, "")
            text = msg.AFTER_WORKOUT_ACHIEVEMENT.format(
                achievement=ach,
                streak_days=streak,
                message=m,
            )
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            text = msg.AFTER_WORKOUT_GOOD.format(
                streak_days=streak,
                days_to_next=days_to_next,
                next_achievement=next_name,
                freezes_left=freezes_left,
            )
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        await query.message.reply_text(msg.MAIN_MENU_TITLE, reply_markup=kb.main_menu_keyboard())
        return

    # ——— Заморозки, напоминания, библиотека ———
    if data == "freeze_use" or data == "freeze_use_now":
        if db.use_freeze(user_id):
            await query.edit_message_text(msg.FREEZE_USED)
        else:
            await query.edit_message_text("Заморозок не осталось или ошибка.")
        await query.message.reply_text(msg.MAIN_MENU_TITLE, reply_markup=kb.main_menu_keyboard())
        return

    if data == "freeze_skip":
        user = db.get_user(user_id)
        prev_streak = user.get("streak_days") or 0
        freezes_left = user.get("freezes_left") or 0
        db.reset_streak(user_id)
        await query.edit_message_text(
            msg.MISSED_DAY.format(
                streak_days=prev_streak,
                freezes_left=freezes_left,
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
        await query.message.reply_text(msg.MAIN_MENU_TITLE, reply_markup=kb.main_menu_keyboard())
        return

    if data.startswith("reminder_"):
        slot = data.replace("reminder_", "")
        if slot == "нет":
            db.update_user(user_id, reminder_time=None)
            await query.edit_message_text("Напоминания отключены. Включить можно в любой момент в меню ⏰ Напоминания.")
        else:
            db.update_user(user_id, reminder_time=slot)
            await query.edit_message_text(f"Готово! Буду напоминать в выбранное время ({slot}).")
        await query.message.reply_text(msg.MAIN_MENU_TITLE, reply_markup=kb.main_menu_keyboard())
        return

    if data.startswith("lib_type_"):
        cat = data.replace("lib_type_", "")
        list_w = wm.get_by_category(cat)
        if not list_w:
            await query.edit_message_text("В этой категории пока нет тренировок.")
            return
        lines = []
        for w in list_w:
            lines.append(f"• {w.get('title', '?')} — {w.get('duration', 0)} мин")
        text = "📚 Тренировки:\n\n" + "\n".join(lines)
        if len(text) > 4000:
            text = text[:3900] + "\n..."
        await query.edit_message_text(text)
        await query.message.reply_text("Ссылки на видео добавляются в библиотеку (workouts.json). Выбери тренировку из меню «Тренировка на сегодня» по опросу 🫶")
        await query.message.reply_text(msg.MAIN_MENU_TITLE, reply_markup=kb.main_menu_keyboard())
        return

    # ——— Онбординг (onb_*, age_*, goal_*, main_menu) ———
    if data == "onb_about":
        await query.edit_message_text(msg.ABOUT_VALUES)
        db.set_user_state(user_id, "onb_name", "")
        await query.message.reply_text(msg.ASK_NAME)
        return

    if data == "onb_skip":
        db.set_user_state(user_id, "onb_name", "")
        await query.edit_message_text(msg.ASK_NAME)
        return

    if data.startswith("age_"):
        age = data.replace("age_", "")
        db.update_user(user_id, age=age)
        db.set_user_state(user_id, "onb_goals", "[]")
        await query.edit_message_text(msg.ASK_GOALS, reply_markup=kb.goals_keyboard())
        return

    if data.startswith("goal_"):
        if data == "goal_done":
            _, state_data = db.get_user_state(user_id)
            try:
                selected = json.loads(state_data or "[]")
            except Exception:
                selected = []
            db.update_user(user_id, goals=selected, onboarding_done=1)
            db.set_user_state(user_id, "", "")
            user = db.get_user(user_id)
            name = user.get("name") or "красотка"
            text = msg.ONBOARDING_END.format(name=name)
            await query.edit_message_text(
                text,
                reply_markup=kb.onboarding_end_keyboard(config.CHAT_LINK),
            )
            await query.message.reply_text(
                msg.MAIN_MENU_TITLE,
                reply_markup=kb.main_menu_keyboard(),
            )
            return
        idx = data.replace("goal_", "")
        try:
            i = int(idx)
        except ValueError:
            return
        _, state_data = db.get_user_state(user_id)
        try:
            selected = json.loads(state_data or "[]")
        except Exception:
            selected = []
        goal_text = msg.GOALS_OPTIONS[i]
        if goal_text in selected:
            selected.remove(goal_text)
        else:
            selected.append(goal_text)
        db.set_user_state(user_id, "onb_goals", json.dumps(selected, ensure_ascii=False))
        await query.edit_message_text(msg.ASK_GOALS, reply_markup=kb.goals_keyboard())
        return

    if data == "main_menu":
        await query.edit_message_text(msg.MAIN_MENU_TITLE)
        await query.message.reply_text(
            msg.MAIN_MENU_TITLE,
            reply_markup=kb.main_menu_keyboard(),
        )


# ——— Один обработчик всех текстовых сообщений (онбординг + главное меню) ———
# В PTB при одном фильтре вызывается только первый обработчик. Два отдельных хендлера
# приводили к тому, что onboarding_message «съедал» обновление и main_menu не вызывался.
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message and not getattr(update, "effective_message", None):
        return
    message = update.effective_message or update.message
    user_id = update.effective_user.id
    text = (message.text or "").strip()

    db.create_user(user_id)
    state, state_data = db.get_user_state(user_id)

    # Состояния онбординга и «вопрос тренеру» / «что помешало»
    if state == "onb_name" and text:
        db.update_user(user_id, name=text)
        db.set_user_state(user_id, "onb_age", "")
        await message.reply_text(msg.ASK_AGE, reply_markup=kb.age_keyboard())
        return

    if state == "coach_question" and text:
        db.add_coach_question(user_id, text)
        db.set_user_state(user_id, "", "")
        if config.TRAINER_CHAT_ID:
            try:
                await context.bot.send_message(
                    config.TRAINER_CHAT_ID,
                    f"Вопрос от {update.effective_user.full_name} (id={user_id}):\n\n{text}",
                )
            except Exception as e:
                logger.warning("Не удалось отправить тренеру: %s", e)
        await message.reply_text(msg.COACH_SENT)
        await message.reply_text(msg.MAIN_MENU_TITLE, reply_markup=kb.main_menu_keyboard())
        return

    if state == "what_stopped" and text:
        db.set_user_state(user_id, "", "")
        await message.reply_text("Записала. В следующий раз обязательно получится 💪")
        await message.reply_text(msg.MAIN_MENU_TITLE, reply_markup=kb.main_menu_keyboard())
        return

    # Остальные состояния онбординга (возраст, цели) — только по callback, сюда не попадают
    if state in ("onb_age", "onb_goals"):
        return

    # Главное меню: только для пользователей, прошедших онбординг
    user = db.get_user(user_id)
    if not user or not user.get("onboarding_done"):
        await start(update, context)
        return

    button = text
    button_lower = button.lower()

    # «Тренировка на сегодня»
    if "тренировка" in button_lower and "сегодня" in button_lower:
        db.set_user_state(user_id, "survey_energy", "")
        await message.reply_text(msg.Q_ENERGY, reply_markup=kb.energy_keyboard())
        return

    if "мой прогресс" in button_lower or "Мой прогресс" in button or button == "🔥 Мой прогресс":
        db.ensure_new_month_reset(user_id)
        user = db.get_user(user_id)
        streak = user.get("streak_days") or 0
        max_streak = user.get("max_streak") or 0
        monthly = user.get("monthly_count") or 0
        freezes_left = user.get("freezes_left") or 0
        achievements = user.get("achievements") or []
        ach_list = "\n".join(f"• {a}" for a in achievements) if achievements else "Пока нет"
        next_name, days_left = get_next_achievement(streak)
        if days_left > 0:
            next_goal = msg.NEXT_GOAL_ACHIEVE.format(achievement=next_name, days=days_left)
        else:
            next_goal = msg.NEXT_GOAL_STREAK.format(days=max_streak - streak) if streak < max_streak else msg.NEXT_GOAL_MONTH.format(left=24 - monthly)
        body = msg.PROGRESS_BODY.format(
            streak_days=streak,
            max_streak=max_streak,
            monthly_count=monthly,
            freezes_left=freezes_left,
            achievements_list=ach_list,
            next_goal=next_goal,
        )
        await message.reply_text(f"*{msg.PROGRESS_HEADER}*\n\n{body}", parse_mode=ParseMode.MARKDOWN)
        return

    if "чат клуба" in button_lower or "Чат клуба" in button or button == "💬 Чат клуба":
        await message.reply_text(f"Перейти в чат клуба: {config.CHAT_LINK}")
        return

    if "напоминания" in button_lower or "Напоминания" in button or button == "⏰ Напоминания":
        await message.reply_text("Выбери удобное время для ежедневного напоминания:", reply_markup=kb.reminder_keyboard())
        return

    if "мои заморозки" in button_lower or "Мои заморозки" in button or button == "❄️ Мои заморозки":
        user = db.get_user(user_id)
        left = user.get("freezes_left") or 0
        used = user.get("freezes_used") or 0
        text_out = msg.FREEZES_SCREEN.format(freezes_left=left, freezes_used=used)
        reply = await message.reply_text(text_out, parse_mode=ParseMode.MARKDOWN)
        if left > 0:
            await reply.reply_text("Потратить заморозку сейчас?", reply_markup=kb.freezes_keyboard(True))
        return

    if "вопрос тренеру" in button_lower or "Вопрос тренеру" in button or button == "❓ Вопрос тренеру":
        db.set_user_state(user_id, "coach_question", "")
        await message.reply_text(msg.COACH_ASK)
        return

    if "библиотека" in button_lower or "Библиотека тренировок" in button or button == "📚 Библиотека тренировок":
        await message.reply_text("Выбери категорию:", reply_markup=kb.library_categories_keyboard())
        return

    # Не распознана кнопка — показываем меню снова
    await message.reply_text("Выбери пункт из меню ниже 👇", reply_markup=kb.main_menu_keyboard())


async def ask_workout_reaction_if_needed(context: ContextTypes.DEFAULT_TYPE):
    """Джоба: спросить про реакцию у тех, кто сегодня проходил опрос и ещё не ответил."""
    # Упрощение: можно вызывать раз в час и проверять survey_answers за сегодня без completed
    pass  # При желании реализовать через БД: выборка user_id по survey_date=today AND completed=0


async def end_of_day_freezes(context: ContextTypes.DEFAULT_TYPE):
    """В конце дня: предложить заморозку тем, кто не тренировался."""
    users = db.get_all_active_users()
    for user_id in users:
        if db.workout_done_today(user_id):
            continue
        user = db.get_user(user_id)
        if (user.get("freezes_left") or 0) < 1:
            db.reset_streak(user_id)
            continue
        try:
            await context.bot.send_message(
                user_id,
                msg.FREEZE_OFFER,
                reply_markup=kb.freeze_offer_keyboard(),
            )
        except Exception as e:
            logger.warning("end_of_day user %s: %s", user_id, e)


async def new_month_reset(context: ContextTypes.DEFAULT_TYPE):
    """В начале месяца: сброс заморозок и счётчика месяца у всех."""
    db.reset_all_monthly()
    users = db.get_all_active_users()
    for user_id in users:
        try:
            await context.bot.send_message(user_id, msg.NEW_MONTH)
        except Exception as e:
            logger.warning("new_month user %s: %s", user_id, e)


async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Отправка утренних/дневных/вечерних напоминаний."""
    job_name = (context.job and getattr(context.job, "name", None)) or (context.job and context.job.id) or ""
    slot = "утро"
    if "day" in str(job_name):
        slot = "день"
    elif "eve" in str(job_name):
        slot = "вечер"
    user_ids = db.get_users_for_reminder(slot)
    name_by_id = {}
    for uid in user_ids:
        u = db.get_user(uid)
        name_by_id[uid] = u.get("name") or "красотка"
    if slot == "утро":
        template = msg.REMINDER_MORNING
    elif slot == "день":
        template = msg.REMINDER_DAY
    else:
        template = msg.REMINDER_EVENING
    for uid in user_ids:
        try:
            name = name_by_id.get(uid, "красотка")
            text = template.format(name=name)
            await context.bot.send_message(uid, text, reply_markup=kb.reminder_choose_training_keyboard())
        except Exception as e:
            logger.warning("reminder user %s: %s", uid, e)


def main():
    db.init_db()
    if not config.BOT_TOKEN:
        env_path = Path(__file__).resolve().parent / ".env"
        logger.error(
            "TELEGRAM_BOT_TOKEN не найден. Создай файл .env в папке с ботом (скопируй env.example в .env) "
            "и укажи в нём: TELEGRAM_BOT_TOKEN=твой_токен_от_BotFather"
        )
        if not env_path.exists():
            logger.info("Файл .env не найден по пути: %s", env_path)
        return

    builder = Application.builder().token(config.BOT_TOKEN)
    if TZ:
        builder.defaults(Defaults(tzinfo=TZ))
    app = builder.build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_error_handler(error_handler)

    # Напоминания и джобы через job_queue (часовой пояс Europe/Moscow)
    jq = app.job_queue
    if jq:
        from telegram.ext import JobQueue
        jq.run_daily(send_reminders, time=dtime(hour=config.REMINDER_TIMES.get("утро", 8), minute=0), name="reminder_morning")
        jq.run_daily(send_reminders, time=dtime(hour=config.REMINDER_TIMES.get("день", 13), minute=0), name="reminder_day")
        jq.run_daily(send_reminders, time=dtime(hour=config.REMINDER_TIMES.get("вечер", 19), minute=0), name="reminder_eve")
        jq.run_daily(end_of_day_freezes, time=dtime(hour=config.END_OF_DAY_HOUR, minute=0), name="end_of_day")
        jq.run_monthly(new_month_reset, when=dtime(hour=0, minute=0), day=1, name="new_month")
        logger.info("Job queue configured")
    else:
        logger.warning("Job queue not available (reminders disabled)")

    logger.info(
        "Бот запущен. Подсказка: если в логе появится «Conflict» — закрой все другие терминалы, "
        "где запущен этот бот (должен быть только один процесс)."
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    import asyncio
    # Python 3.10+: в главном потоке может не быть event loop — создаём при необходимости
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    main()
