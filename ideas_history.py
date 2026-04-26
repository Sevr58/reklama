"""
История идей — отслеживает, какие темы уже были предложены,
чтобы не повторять их в следующих исследованиях.

Статусы:
  used      — пост по идее опубликован, больше не предлагать никогда
  removed   — пользователь явно убрал тему, не предлагать никогда
  postponed — отложено на текущий день; через 20+ часов снова в выдаче

Хранилище: ideas_history.json в корне проекта.
"""

import json
import re
import time
from pathlib import Path

HISTORY_FILE = Path(__file__).parent / "ideas_history.json"

# Откладываем считается "свежим" 20 часов — после этого тема снова в выдаче
POSTPONE_TTL_SECONDS = 20 * 3600


def _normalize(text: str) -> str:
    """Приводит идею к ключу: lowercase + только буквы/цифры/пробелы."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_history(history: dict):
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _set_status(idea_text: str, status: str, title: str = None):
    history = load_history()
    key = _normalize(idea_text)
    if not key:
        return
    history[key] = {
        "status": status,
        "ts": time.time(),
        "title": title or idea_text[:200],
    }
    save_history(history)


def mark_used(idea_text: str, title: str = None):
    _set_status(idea_text, "used", title)


def mark_postponed(idea_text: str, title: str = None):
    _set_status(idea_text, "postponed", title)


def mark_removed(idea_text: str, title: str = None):
    _set_status(idea_text, "removed", title)


def get_status(idea_text: str) -> str | None:
    history = load_history()
    return (history.get(_normalize(idea_text)) or {}).get("status")


def is_blocked(idea_text: str) -> bool:
    """True — идею нельзя показывать в выдаче."""
    history = load_history()
    entry = history.get(_normalize(idea_text))
    if not entry:
        return False
    status = entry.get("status")
    if status in ("used", "removed"):
        return True
    if status == "postponed":
        age = time.time() - entry.get("ts", 0)
        return age < POSTPONE_TTL_SECONDS
    return False


def get_blocked_titles(limit: int = 60) -> list[str]:
    """Список заголовков used+removed для подсказки Claude (не предлагать заново)."""
    history = load_history()
    titles = []
    for entry in history.values():
        if entry.get("status") in ("used", "removed"):
            t = entry.get("title")
            if t:
                titles.append(t)
    return titles[-limit:]
