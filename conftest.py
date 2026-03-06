# -*- coding: utf-8 -*-
"""Фикстуры для тестов бота «Тело говорит»."""
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def test_db_path():
    """Временная БД для каждого теста (не трогаем bot_data.db)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def patch_config(test_db_path):
    """Подмена путей конфига на тестовые до и после каждого теста."""
    import config
    original_db = getattr(config, "DB_PATH", None)
    original_workouts = getattr(config, "WORKOUTS_JSON", None)
    config.DB_PATH = Path(test_db_path)
    base = Path(__file__).resolve().parent
    config.WORKOUTS_JSON = base / "workouts.json"
    yield
    config.DB_PATH = original_db
    config.WORKOUTS_JSON = original_workouts


@pytest.fixture
def db():
    """Импорт database после применения patch_config."""
    import database as db
    db.init_db()
    return db
