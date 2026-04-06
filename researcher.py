"""
Ежедневный исследователь контента.
Ищет свежие идеи в иностранных источниках:
- RSS-ленты AdAge, AdWeek, The Drum, Campaign
- YouTube — ролики по рекламе и маркетингу
Генерирует 5-7 идей для постов и отправляет на выбор.
"""

import sys
import json
import logging
import feedparser
import subprocess
import anthropic
from config import ANTHROPIC_API_KEY

log = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# RSS-источники
RSS_FEEDS = [
    ("AdAge",     "https://adage.com/rss/headlines"),
    ("AdWeek",    "https://www.adweek.com/feed/"),
    ("The Drum",  "https://www.thedrum.com/rss.xml"),
    ("Campaign",  "https://www.campaignlive.co.uk/rss"),
    ("Shots",     "https://shots.net/feed"),
]

# YouTube-запросы для поиска роликов
YOUTUBE_QUERIES = [
    "advertising creative strategy 2025",
    "best TV commercials breakdown",
    "advertising copywriting tips",
    "brand storytelling marketing",
    "ad campaign case study",
]


def fetch_rss_headlines(max_per_feed: int = 5) -> list[dict]:
    """Собирает свежие заголовки из RSS-лент."""
    items = []
    for source, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                items.append({
                    "source": source,
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:300],
                    "link": entry.get("link", ""),
                })
            log.info(f"RSS {source}: {len(feed.entries[:max_per_feed])} статей")
        except Exception as e:
            log.warning(f"RSS {source} ошибка: {e}")
    return items


def fetch_youtube_ideas(max_videos: int = 3) -> list[dict]:
    """Ищет релевантные ролики на YouTube и берёт их описания."""
    import random
    query = random.choice(YOUTUBE_QUERIES)
    videos = []

    try:
        result = subprocess.run(
            [sys.executable, "-m", "yt_dlp",
             f"ytsearch{max_videos}:{query}",
             "--dump-json", "--no-download", "--quiet"],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                videos.append({
                    "source": "YouTube",
                    "title": data.get("title", ""),
                    "summary": (data.get("description") or "")[:300],
                    "link": f"https://youtube.com/watch?v={data.get('id','')}",
                    "channel": data.get("uploader", ""),
                })
            except Exception:
                continue
        log.info(f"YouTube: найдено {len(videos)} роликов по запросу «{query}»")
    except Exception as e:
        log.warning(f"YouTube поиск ошибка: {e}")

    return videos


def generate_ideas(items: list[dict]) -> list[dict]:
    """
    Передаёт найденный контент в Claude.
    Возвращает список из 5-7 идей для постов.
    """
    content_summary = "\n".join([
        f"[{i['source']}] {i['title']}\n{i['summary']}"
        for i in items[:20]
    ])

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"""Ты — контент-стратег для Telegram-канала рекламного продюсера Евгения Севрюгина (Россия, 25 лет опыта).

Вот свежий контент из иностранных источников о рекламе и маркетинге:

{content_summary}

Твоя задача: на основе этих материалов придумай 6 идей для постов в Telegram-канале Евгения.

Требования к идеям:
- Адаптируй иностранный опыт под российский рынок и аудиторию
- Тема должна быть актуальной для предпринимателей, которые заказывают рекламу
- Идея должна звучать как тема для авторского поста — мнение, разбор, история, совет
- Никаких "топ-10 советов" и других банальных форматов

Верни JSON-массив строго в таком формате (без markdown):
[
  {{
    "idea": "Краткое название идеи (до 10 слов)",
    "angle": "Угол подачи — что именно скажет Евгений (1-2 предложения)",
    "source": "Откуда вдохновение (название источника)"
  }}
]"""
        }]
    )

    raw = message.content[0].text.strip()
    import re
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


def run_research() -> list[dict]:
    """Полный цикл: собрать контент → сгенерировать идеи."""
    log.info("Запускаю ежедневное исследование...")

    rss_items = fetch_rss_headlines()
    yt_items = fetch_youtube_ideas()
    all_items = rss_items + yt_items

    if not all_items:
        log.warning("Не удалось собрать контент из источников")
        return []

    ideas = generate_ideas(all_items)
    log.info(f"Сгенерировано идей: {len(ideas)}")
    return ideas
