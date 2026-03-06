# -*- coding: utf-8 -*-
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔥 Тренировка на сегодня")],
            [KeyboardButton("📚 Библиотека тренировок"), KeyboardButton("🔥 Мой прогресс")],
            [KeyboardButton("💬 Чат клуба"), KeyboardButton("⏰ Напоминания")],
            [KeyboardButton("❄️ Мои заморозки"), KeyboardButton("❓ Вопрос тренеру")],
        ],
        resize_keyboard=True,
    )


def welcome_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👉 Познакомимся", callback_data="onb_about")],
        [InlineKeyboardButton("🔥 Сразу в клуб", callback_data="onb_skip")],
    ])


def onboarding_end_keyboard(chat_link: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Перейти в чат", url=chat_link)],
        [InlineKeyboardButton("🏠 На главную", callback_data="main_menu")],
    ])


def age_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("до 25", callback_data="age_до 25"),
            InlineKeyboardButton("25-30", callback_data="age_25-30"),
        ],
        [
            InlineKeyboardButton("30-35", callback_data="age_30-35"),
            InlineKeyboardButton("35+", callback_data="age_35+"),
        ],
    ])


def goals_keyboard():
    from messages import GOALS_OPTIONS
    buttons = []
    for i, g in enumerate(GOALS_OPTIONS):
        buttons.append([InlineKeyboardButton(g, callback_data=f"goal_{i}")])
    buttons.append([InlineKeyboardButton("✅ Готово", callback_data="goal_done")])
    return InlineKeyboardMarkup(buttons)


def energy_keyboard():
    from messages import ENERGY_OPTIONS
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t, callback_data=f"survey_energy_{v}")] for t, v in ENERGY_OPTIONS
    ])


def cycle_keyboard():
    from messages import CYCLE_OPTIONS
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t, callback_data=f"survey_cycle_{v}")] for t, v in CYCLE_OPTIONS
    ])


def time_keyboard():
    from messages import TIME_OPTIONS
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t, callback_data=f"survey_time_{v}")] for t, v in TIME_OPTIONS
    ])


def goal_today_keyboard():
    from messages import GOAL_TODAY_OPTIONS
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t, callback_data=f"survey_goal_{v}")] for t, v in GOAL_TODAY_OPTIONS
    ])


def workout_start_keyboard(link: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Начать тренировку", url=link)],
    ])


def reaction_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❤️ Супер", callback_data="reaction_супер"),
            InlineKeyboardButton("💪 Молодец", callback_data="reaction_молодец"),
            InlineKeyboardButton("🥺 Слилась", callback_data="reaction_слилась"),
        ],
    ])


def freeze_offer_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❄️ Потратить", callback_data="freeze_use")],
        [InlineKeyboardButton("Нет, пусть гаснет", callback_data="freeze_skip")],
    ])


def reminder_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌅 Утро", callback_data="reminder_утро"),
            InlineKeyboardButton("☀️ День", callback_data="reminder_день"),
        ],
        [
            InlineKeyboardButton("🌆 Вечер", callback_data="reminder_вечер"),
            InlineKeyboardButton("Не надо", callback_data="reminder_нет"),
        ],
    ])


def reminder_choose_training_keyboard():
    from messages import CHOOSE_TRAINING
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(CHOOSE_TRAINING, callback_data="start_survey")],
    ])


def freezes_keyboard(has_freeze: bool):
    buttons = []
    if has_freeze:
        buttons.append([InlineKeyboardButton("Потратить заморозку сейчас", callback_data="freeze_use_now")])
    return InlineKeyboardMarkup(buttons) if buttons else None


def library_categories_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💪 Силовые", callback_data="lib_type_силовая")],
        [InlineKeyboardButton("🧘 Растяжка", callback_data="lib_type_растяжка")],
        [InlineKeyboardButton("🌬 Дыхание", callback_data="lib_type_дыхание")],
        [InlineKeyboardButton("⚡ Экспресс (до 10 мин)", callback_data="lib_type_экспресс")],
        [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")],
    ])
