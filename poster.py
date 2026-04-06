import asyncio
import logging
import requests
import telegram
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, UPLOAD_POST_TOKEN, UPLOAD_POST_USERNAME

log = logging.getLogger(__name__)


async def _send_to_telegram(text: str, image_path: str = None):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

    if image_path:
        with open(image_path, "rb") as photo:
            if len(text) <= 1024:
                await bot.send_photo(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    photo=photo,
                    caption=text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=photo)
                await bot.send_message(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    text=text,
                    parse_mode="HTML"
                )
    else:
        await bot.send_message(
            chat_id=TELEGRAM_CHANNEL_ID,
            text=text,
            parse_mode="HTML"
        )


def post_telegram(text: str, image_path: str = None):
    """Публикует пост в Telegram-канал."""
    asyncio.run(_send_to_telegram(text, image_path))
    log.info(f"[Telegram] Опубликовано: {text[:60]}...")


def post_social(text: str, image_path: str = None, platforms: list = None):
    """Публикует текст + картинку в указанные платформы через upload-post.com."""
    if platforms is None:
        platforms = ["instagram", "facebook", "x"]

    caption = text[:2200]
    headers = {"Authorization": f"Apikey {UPLOAD_POST_TOKEN}"}

    if image_path:
        with open(image_path, "rb") as img:
            data = {"user": UPLOAD_POST_USERNAME, "title": caption}
            for p in platforms:
                data["platform[]"] = p
            r = requests.post(
                "https://api.upload-post.com/api/upload_photos",
                headers=headers,
                files={"photos[]": open(image_path, "rb")},
                data=data,
                timeout=60
            )
    else:
        data = {"user": UPLOAD_POST_USERNAME, "title": caption}
        for p in platforms:
            data["platform[]"] = p
        r = requests.post(
            "https://api.upload-post.com/api/upload_text",
            headers=headers,
            data=data,
            timeout=60
        )

    log.info(f"[Social] {platforms} HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")


def post_video(text: str, video_path: str, platforms: list = None):
    """Публикует вертикальное видео в YouTube Shorts и Instagram Reels."""
    if platforms is None:
        platforms = ["youtube", "instagram"]

    caption = text[:2200]
    headers = {"Authorization": f"Apikey {UPLOAD_POST_TOKEN}"}

    with open(video_path, "rb") as vid:
        data = {
            "user": UPLOAD_POST_USERNAME,
            "title": caption,
            "is_short": "true",   # YouTube Shorts
            "is_reel": "true",    # Instagram Reels
        }
        for p in platforms:
            data["platform[]"] = p

        r = requests.post(
            "https://api.upload-post.com/api/upload_video",
            headers=headers,
            files={"video": vid},
            data=data,
            timeout=120
        )

    log.info(f"[Video] {platforms} HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")
