"""
Ежедневный исследователь контента.
Ищет свежие идеи в русско- и англоязычных источниках:
- RSS-ленты: Sostav, Adindex, Cossa, vc.ru, Texterra, Habr, Rusbase (RU)
             + AdAge, AdWeek, The Drum (EN)
- YouTube-поиск по запросам (реклама 70% / маркетинг 30%)
- Авторские YouTube-каналы (мониторинг последних видео)
Генерирует 6 идей для постов и отправляет на выбор.
"""

import sys
import json
import random
import logging
import feedparser
import subprocess
import anthropic
from config import ANTHROPIC_API_KEY
import ideas_history

log = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ─── RSS-источники ────────────────────────────────────────────────────────────

# Русскоязычные — реклама
RSS_FEEDS_RU_AD = [
    ("Sostav",          "https://www.sostav.ru/rss/news.xml"),
    ("Adindex",         "https://adindex.ru/rss/news.phtml"),
]
# Русскоязычные — маркетинг / digital
RSS_FEEDS_RU_MKT = [
    ("Cossa",           "https://www.cossa.ru/rss/"),
    ("vc.ru/marketing", "https://vc.ru/rss/marketing"),
    ("Texterra",        "https://texterra.ru/blog/rss.xml"),
    ("Habr/маркетинг",  "https://habr.com/ru/rss/hub/marketing/all/"),
    ("Rusbase",         "https://rb.ru/feeds/news/"),
]
# Англоязычные — реклама
RSS_FEEDS_EN = [
    ("AdAge",           "https://adage.com/rss/headlines"),
    ("AdWeek",          "https://www.adweek.com/feed/"),
    ("The Drum",        "https://www.thedrum.com/rss.xml"),
]

RSS_FEEDS = RSS_FEEDS_RU_AD + RSS_FEEDS_RU_MKT + RSS_FEEDS_EN


# ─── YouTube-поиск по запросам ────────────────────────────────────────────────

# ~70% реклама
YOUTUBE_QUERIES_AD = [
    "разбор рекламного ролика кейс",
    "создание рекламы для бизнеса Россия",
    "рекламная кампания разбор пример",
    "advertising creative strategy 2025",
    "best TV commercials breakdown",
    "ad campaign case study",
]
# ~30% маркетинг
YOUTUBE_QUERIES_MKT = [
    "маркетинг стратегия для бизнеса",
    "позиционирование бренда примеры",
    "brand storytelling marketing",
]
YOUTUBE_QUERIES = YOUTUBE_QUERIES_AD + YOUTUBE_QUERIES_MKT


# ─── Авторские YouTube-каналы ─────────────────────────────────────────────────
# Формат: (название, URL канала)
# Если канал недоступен — yt-dlp тихо пропустит, ничего не сломается.

YOUTUBE_CHANNELS = [
    # Копирайтинг и тексты
    ("Максим Ильяхов",        "https://www.youtube.com/@ilyahov"),
    ("Дмитрий Кот",           "https://www.youtube.com/@dmitriykot"),
    # Digital-реклама и аналитика
    ("eLama",                  "https://www.youtube.com/@elama"),
    ("Texterra",               "https://www.youtube.com/@texterra"),
    # SMM и соцсети
    ("Саша Чижов",             "https://www.youtube.com/@alexanderchizhov"),
    ("Михаил Христосенко",     "https://www.youtube.com/@khristosenko"),
    # Маркетинг и стратегия
    ("Websarafan",             "https://www.youtube.com/@websarafan"),
    ("Нетология",              "https://www.youtube.com/@netologyru"),
    ("Skillbox Маркетинг",     "https://www.youtube.com/@skillbox"),
    # Реклама и бренды
    ("Рекламные Идеи",         "https://www.youtube.com/@reklamnye_idei"),
    ("Sostav.ru",              "https://www.youtube.com/@sostav"),
    ("Игорь Манн",             "https://www.youtube.com/@igormann"),
]


# ─── Функции сбора данных ─────────────────────────────────────────────────────

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
    """Ищет ролики по случайному запросу (70% реклама / 30% маркетинг)."""
    pool = YOUTUBE_QUERIES_AD * 7 + YOUTUBE_QUERIES_MKT * 3
    query = random.choice(pool)
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
                    "source": "YouTube/поиск",
                    "title": data.get("title", ""),
                    "summary": (data.get("description") or "")[:300],
                    "link": f"https://youtube.com/watch?v={data.get('id', '')}",
                    "channel": data.get("uploader", ""),
                })
            except Exception:
                continue
        log.info(f"YouTube поиск «{query}»: {len(videos)} роликов")
    except Exception as e:
        log.warning(f"YouTube поиск ошибка: {e}")

    return videos


def fetch_channel_videos(channels_per_run: int = 4, max_per_channel: int = 2) -> list[dict]:
    """Берёт последние видео с нескольких случайных авторских каналов."""
    sample = random.sample(YOUTUBE_CHANNELS, min(channels_per_run, len(YOUTUBE_CHANNELS)))
    items = []

    for name, url in sample:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "yt_dlp",
                 url,
                 "--dump-json", "--no-download", "--quiet",
                 "--playlist-end", str(max_per_channel)],
                capture_output=True, text=True, timeout=40
            )
            count = 0
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    items.append({
                        "source": f"YouTube/{name}",
                        "title": data.get("title", ""),
                        "summary": (data.get("description") or "")[:300],
                        "link": f"https://youtube.com/watch?v={data.get('id', '')}",
                        "channel": name,
                    })
                    count += 1
                except Exception:
                    continue
            if count:
                log.info(f"Канал {name}: {count} видео")
            else:
                log.debug(f"Канал {name}: видео не получены (канал недоступен или пустой)")
        except Exception as e:
            log.warning(f"Канал {name} ошибка: {e}")

    return items


# ─── Генерация идей ───────────────────────────────────────────────────────────

def generate_ideas(items: list[dict]) -> list[dict]:
    """Передаёт собранный контент в Claude → возвращает 6 идей для постов."""
    content_summary = "\n".join([
        f"[{i['source']}] {i['title']}\n{i['summary']}"
        for i in items[:25]
    ])

    blocked = ideas_history.get_blocked_titles(limit=60)
    blocked_block = ""
    if blocked:
        blocked_list = "\n".join(f"- {t}" for t in blocked)
        blocked_block = (
            f"\n\nВот темы, которые УЖЕ были предложены ранее — НЕ повторяй их и не предлагай близкие переформулировки:\n{blocked_list}\n"
        )

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"""Ты — контент-стратег для Telegram-канала рекламного продюсера Евгения Севрюгина (Россия, 25 лет опыта).

Вот свежий контент из российских и зарубежных источников о рекламе и маркетинге:

{content_summary}
{blocked_block}
Твоя задача: на основе этих материалов придумай 6 идей для постов в Telegram-канале Евгения.

Пропорция тем:
- ~4 идеи про рекламу: креатив, кейсы, рекламные кампании, ТВ-реклама, продакшн
- ~2 идеи про маркетинг: стратегия, позиционирование, работа с брендом

Требования к идеям:
- Для идей из зарубежных источников — адаптируй под российский рынок и аудиторию
- Тема должна быть актуальной для предпринимателей, которые заказывают рекламу
- Идея должна звучать как тема для авторского поста — мнение, разбор, история, совет
- Никаких "топ-10 советов" и других банальных форматов
- ВАЖНО: не повторяй темы из списка выше (used/removed) — нужны свежие, не похожие на ранее предложенные

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
    ideas = json.loads(raw)

    # Постобработка: на всякий случай отфильтровываем то, что уже есть в истории
    fresh = []
    for idea in ideas:
        title = idea.get("idea", "")
        if not title:
            continue
        if ideas_history.is_blocked(title):
            log.info(f"LLM повторила заблокированную идею, отбрасываю: {title[:60]}")
            continue
        fresh.append(idea)
    return fresh


# ─── Основной цикл ────────────────────────────────────────────────────────────

def run_research() -> list[dict]:
    """Полный цикл: собрать контент → сгенерировать идеи."""
    log.info("Запускаю ежедневное исследование...")

    rss_items     = fetch_rss_headlines()
    yt_search     = fetch_youtube_ideas()
    yt_channels   = fetch_channel_videos()
    all_items     = rss_items + yt_search + yt_channels

    log.info(f"Всего материалов: {len(all_items)} "
             f"(RSS: {len(rss_items)}, поиск YT: {len(yt_search)}, каналы YT: {len(yt_channels)})")

    if not all_items:
        log.warning("Не удалось собрать контент из источников")
        return []

    ideas = generate_ideas(all_items)
    log.info(f"Сгенерировано идей: {len(ideas)}")
    return ideas
