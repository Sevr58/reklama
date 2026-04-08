import logging
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, UPLOAD_POST_TOKEN, UPLOAD_POST_USERNAME

log = logging.getLogger(__name__)

TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def post_telegram(text: str, image_path: str = None):
    """Публикует пост в Telegram-канал через прямой HTTP-запрос (без asyncio)."""
    if image_path:
        try:
            with open(image_path, "rb") as photo:
                if len(text) <= 1024:
                    r = requests.post(
                        f"{TG_API}/sendPhoto",
                        data={"chat_id": TELEGRAM_CHANNEL_ID, "caption": text, "parse_mode": "HTML"},
                        files={"photo": photo},
                        timeout=30,
                    )
                else:
                    r = requests.post(
                        f"{TG_API}/sendPhoto",
                        data={"chat_id": TELEGRAM_CHANNEL_ID},
                        files={"photo": photo},
                        timeout=30,
                    )
                    r.raise_for_status()
                    requests.post(
                        f"{TG_API}/sendMessage",
                        json={"chat_id": TELEGRAM_CHANNEL_ID, "text": text, "parse_mode": "HTML"},
                        timeout=30,
                    ).raise_for_status()
                    log.info(f"[Telegram] Опубликовано с фото: {text[:60]}...")
                    return
        except FileNotFoundError:
            log.warning(f"[Telegram] Файл не найден: {image_path}, публикую без фото")
            image_path = None

    if not image_path:
        r = requests.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": TELEGRAM_CHANNEL_ID, "text": text, "parse_mode": "HTML"},
            timeout=30,
        )

    r.raise_for_status()
    log.info(f"[Telegram] Опубликовано: {text[:60]}...")


def post_social(text: str, image_path: str = None, platforms: list = None):
    """Публикует текст + картинку в указанные платформы через upload-post.com."""
    if not UPLOAD_POST_TOKEN or not UPLOAD_POST_USERNAME:
        log.warning("[Social] UPLOAD_POST_TOKEN или USERNAME не заданы — пропускаю")
        return

    if platforms is None:
        platforms = ["instagram", "facebook", "x"]

    caption = text[:2200]
    headers = {"Authorization": f"Apikey {UPLOAD_POST_TOKEN}"}

    data = {"user": UPLOAD_POST_USERNAME, "title": caption}
    for p in platforms:
        data["platform[]"] = p

    if image_path:
        try:
            with open(image_path, "rb") as img:
                r = requests.post(
                    "https://api.upload-post.com/api/upload_photos",
                    headers=headers,
                    files={"photos[]": img},
                    data=data,
                    timeout=60,
                )
        except FileNotFoundError:
            log.warning(f"[Social] Файл не найден: {image_path}, публикую без фото")
            r = requests.post(
                "https://api.upload-post.com/api/upload_text",
                headers=headers,
                data=data,
                timeout=60,
            )
    else:
        r = requests.post(
            "https://api.upload-post.com/api/upload_text",
            headers=headers,
            data=data,
            timeout=60,
        )

    log.info(f"[Social] {platforms} HTTP {r.status_code}: {r.text[:200]}")
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")


def post_video(text: str, video_path: str, platforms: list = None):
    """Публикует вертикальное видео в YouTube Shorts и Instagram Reels."""
    if not UPLOAD_POST_TOKEN or not UPLOAD_POST_USERNAME:
        log.warning("[Video] UPLOAD_POST_TOKEN не задан — пропускаю")
        return

    if platforms is None:
        platforms = ["youtube", "instagram"]

    caption = text[:2200]
    headers = {"Authorization": f"Apikey {UPLOAD_POST_TOKEN}"}

    data = {
        "user": UPLOAD_POST_USERNAME,
        "title": caption,
        "is_short": "true",
        "is_reel": "true",
    }
    for p in platforms:
        data["platform[]"] = p

    with open(video_path, "rb") as vid:
        r = requests.post(
            "https://api.upload-post.com/api/upload_video",
            headers=headers,
            files={"video": vid},
            data=data,
            timeout=120,
        )

    log.info(f"[Video] {platforms} HTTP {r.status_code}: {r.text[:200]}")
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")
