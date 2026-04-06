"""
Поиск реальных рекламных роликов на YouTube.
Если пост упоминает конкретную рекламу — находим её, берём превью и ссылку.
"""

import subprocess
import sys
import json
import requests
import logging

log = logging.getLogger(__name__)


def extract_ad_reference(post_text: str, claude_client) -> str | None:
    """
    Спрашивает Claude: упоминается ли в посте конкретный реальный рекламный ролик?
    Если да — возвращает поисковый запрос для YouTube.
    Если нет — возвращает None.
    """
    import anthropic

    message = claude_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": f"""Прочитай этот текст поста и ответь на вопрос:
упоминается ли в нём конкретный реальный рекламный ролик или рекламная кампания бренда?

Если да — напиши поисковый запрос для YouTube (на английском), чтобы найти этот ролик.
Формат ответа: только поисковый запрос, ничего лишнего.
Если нет — напиши только слово: НЕТ

Текст поста:
{post_text}"""
            }
        ]
    )

    result = message.content[0].text.strip()

    if result.upper() == "НЕТ" or "нет" in result.lower()[:10]:
        return None

    return result


def find_youtube_video(search_query: str) -> dict | None:
    """
    Ищет видео на YouTube через yt-dlp (без API-ключа).
    Возвращает словарь с id, title, url, thumbnail.
    """
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "yt_dlp",
                f"ytsearch1:{search_query}",
                "--dump-json",
                "--no-download",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0 or not result.stdout.strip():
            log.warning(f"yt-dlp ничего не нашёл для: {search_query}")
            return None

        data = json.loads(result.stdout.strip())

        return {
            "id": data.get("id"),
            "title": data.get("title"),
            "url": f"https://www.youtube.com/watch?v={data.get('id')}",
            "thumbnail": data.get("thumbnail"),
        }

    except Exception as e:
        log.warning(f"Ошибка поиска на YouTube: {e}")
        return None


def download_thumbnail(video: dict, save_path: str = "temp_image.png") -> str | None:
    """
    Скачивает превью YouTube-видео.
    Пробует maxresdefault, потом hqdefault.
    """
    video_id = video.get("id")
    if not video_id:
        return None

    for quality in ["maxresdefault", "hqdefault", "mqdefault"]:
        url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and len(response.content) > 5000:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                log.info(f"Превью скачано ({quality}): {url}")
                return save_path
        except Exception as e:
            log.warning(f"Не удалось скачать превью {quality}: {e}")

    return None
