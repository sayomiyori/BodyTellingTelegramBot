# -*- coding: utf-8 -*-
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Токен бота от @BotFather
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ID администраторов (твой Telegram user id для админки)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip()]

# Ссылка на закрытый чат клуба
CHAT_LINK = os.getenv("CHAT_LINK", "https://t.me/your_club_chat")

# ID чата/лички тренера для пересылки вопросов (или None)
TRAINER_CHAT_ID = os.getenv("TRAINER_CHAT_ID")
if TRAINER_CHAT_ID:
    TRAINER_CHAT_ID = int(TRAINER_CHAT_ID)

# Время напоминаний (часы по Москве или UTC — подстроить под сервер)
REMINDER_TIMES = {
    "утро": 8,
    "день": 13,
    "вечер": 19,
}

# Час проверки "конца дня" для предложения заморозки (например 22)
END_OF_DAY_HOUR = 22

# Путь к БД и библиотеке тренировок
DB_PATH = BASE_DIR / "bot_data.db"
WORKOUTS_JSON = BASE_DIR / "workouts.json"
