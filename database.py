# -*- coding: utf-8 -*-
import sqlite3
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import config


def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = 1")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            age TEXT,
            goals TEXT,
            streak_days INTEGER DEFAULT 0,
            max_streak INTEGER DEFAULT 0,
            freezes_left INTEGER DEFAULT 3,
            freezes_used INTEGER DEFAULT 0,
            last_workout_date TEXT,
            achievements TEXT DEFAULT '[]',
            monthly_count INTEGER DEFAULT 0,
            reminder_time TEXT,
            is_active INTEGER DEFAULT 1,
            onboarding_done INTEGER DEFAULT 0,
            state TEXT,
            state_data TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS survey_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            survey_date TEXT NOT NULL,
            energy TEXT,
            cycle_phase TEXT,
            time_slot TEXT,
            goal TEXT,
            workout_id TEXT,
            completed INTEGER DEFAULT 0,
            reaction TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS coach_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    """)
    conn.commit()
    conn.close()


def get_user(user_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_user(row)


def _row_to_user(row) -> dict:
    d = dict(row)
    if d.get("goals"):
        try:
            d["goals"] = json.loads(d["goals"])
        except Exception:
            d["goals"] = []
    else:
        d["goals"] = []
    if d.get("achievements"):
        try:
            d["achievements"] = json.loads(d["achievements"])
        except Exception:
            d["achievements"] = []
    else:
        d["achievements"] = []
    return d


def create_user(user_id: int):
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR IGNORE INTO users
           (user_id, streak_days, max_streak, freezes_left, freezes_used,
            achievements, monthly_count, onboarding_done, created_at, updated_at)
           VALUES (?, 0, 0, 3, 0, '[]', 0, 0, ?, ?)""",
        (user_id, now, now),
    )
    conn.commit()
    conn.close()


def set_user_state(user_id: int, state: str, state_data: str = None):
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE users SET state = ?, state_data = ?, updated_at = ? WHERE user_id = ?",
        (state, state_data or "", now, user_id),
    )
    conn.commit()
    conn.close()


def get_user_state(user_id: int) -> tuple:
    u = get_user(user_id)
    if not u:
        return None, None
    return u.get("state"), u.get("state_data") or ""


def update_user(user_id: int, **kwargs):
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    allowed = {
        "name", "age", "goals", "streak_days", "max_streak",
        "freezes_left", "freezes_used", "last_workout_date",
        "achievements", "monthly_count", "reminder_time", "is_active",
        "onboarding_done", "state", "state_data",
    }
    for key, val in kwargs.items():
        if key not in allowed:
            continue
        if key == "goals" or key == "achievements":
            val = json.dumps(val, ensure_ascii=False) if val is not None else "[]"
        conn.execute(
            f"UPDATE users SET {key} = ?, updated_at = ? WHERE user_id = ?",
            (val, now, user_id),
        )
    conn.commit()
    conn.close()


def ensure_new_month_reset(user_id: int) -> bool:
    """Сброс счётчиков месяца при смене месяца. Возвращает True если был сброс."""
    u = get_user(user_id)
    if not u:
        return False
    today = date.today()
    # Определяем месяц последнего обновления (по last_workout или updated_at)
    last = u.get("last_workout_date") or u.get("updated_at") or ""
    if not last:
        return False
    try:
        parts = last.split(" ")[0].split("T")[0].split("-")
        if len(parts) >= 2:
            last_month = (int(parts[0]), int(parts[1]))
            if (today.year, today.month) > last_month:
                update_user(
                    user_id,
                    freezes_left=3,
                    freezes_used=0,
                    monthly_count=0,
                )
                return True
    except Exception:
        pass
    return False


def record_workout_done(user_id: int) -> dict:
    """Увеличивает streak, monthly_count, обновляет last_workout_date, проверяет достижения."""
    u = get_user(user_id)
    if not u:
        return {}
    today = date.today().isoformat()
    streak = (u.get("streak_days") or 0) + 1
    max_streak = max(u.get("max_streak") or 0, streak)
    monthly = (u.get("monthly_count") or 0) + 1
    achievements = list(u.get("achievements") or [])
    new_achievement = None

    thresholds = [
        (1, "Первый шаг"),
        (3, "Огонёк зажёгся"),
        (7, "На связи с телом"),
        (14, "Привычка закрепляется"),
        (30, "Мастерица бережности"),
        (60, "Нереально крутая"),
        (90, "Богиня регулярности"),
    ]
    for days, name in thresholds:
        if streak >= days and name not in achievements:
            achievements.append(name)
            new_achievement = name
            break

    update_user(
        user_id,
        streak_days=streak,
        max_streak=max_streak,
        monthly_count=monthly,
        last_workout_date=today,
        achievements=achievements,
    )
    return {
        "streak_days": streak,
        "max_streak": max_streak,
        "monthly_count": monthly,
        "new_achievement": new_achievement,
        "freezes_left": u.get("freezes_left") or 0,
    }


def use_freeze(user_id: int) -> bool:
    u = get_user(user_id)
    if not u or (u.get("freezes_left") or 0) < 1:
        return False
    update_user(
        user_id,
        freezes_left=(u.get("freezes_left") or 0) - 1,
        freezes_used=(u.get("freezes_used") or 0) + 1,
    )
    return True


def reset_streak(user_id: int):
    update_user(user_id, streak_days=0)


def save_survey(user_id: int, energy: str, cycle: str, time_slot: str, goal: str, workout_id: str = None):
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    today = date.today().isoformat()
    conn.execute(
        """INSERT INTO survey_answers
           (user_id, survey_date, energy, cycle_phase, time_slot, goal, workout_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, today, energy, cycle, time_slot, goal, workout_id or "", now),
    )
    conn.commit()
    conn.close()


def set_survey_completed(user_id: int, reaction: str = None):
    conn = get_connection()
    today = date.today().isoformat()
    conn.execute(
        "UPDATE survey_answers SET completed = 1, reaction = ? WHERE user_id = ? AND survey_date = ?",
        (reaction or "", user_id, today),
    )
    conn.commit()
    conn.close()


def workout_done_today(user_id: int) -> bool:
    conn = get_connection()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT 1 FROM survey_answers WHERE user_id = ? AND survey_date = ? AND completed = 1",
        (user_id, today),
    ).fetchone()
    conn.close()
    return bool(row)


def add_coach_question(user_id: int, text: str):
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO coach_questions (user_id, text, created_at) VALUES (?, ?, ?)",
        (user_id, text, now),
    )
    conn.commit()
    conn.close()


def get_users_for_reminder(reminder_slot: str) -> list:
    """reminder_slot: утро, день, вечер"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT user_id FROM users WHERE reminder_time = ? AND is_active = 1",
        (reminder_slot,),
    ).fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


def get_all_active_users() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT user_id FROM users WHERE is_active = 1").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


def user_count():
    conn = get_connection()
    c = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return c


def reset_all_monthly():
    """Сброс заморозок и месячного счётчика у всех пользователей (вызов в 1-й день месяца)."""
    conn = get_connection()
    conn.execute(
        "UPDATE users SET freezes_left = 3, freezes_used = 0, monthly_count = 0"
    )
    conn.commit()
    conn.close()
