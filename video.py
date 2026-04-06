"""
Генерация коротких вертикальных видео через Google Veo 3.
Используется для YouTube Shorts и Instagram Reels.
"""

import time
import logging
from pathlib import Path

from google import genai
from google.genai import types

from config import GEMINI_API_KEY

log = logging.getLogger(__name__)

MODEL = "veo-3.0-generate-001"
OUTPUT_DIR = Path(__file__).parent / "generated_videos"
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_video_prompt(post_text: str) -> str:
    """Создаёт промпт для видео на основе текста поста."""
    short = post_text[:150].replace("\n", " ").strip()
    return (
        f"Elegant vertical video for premium social media. "
        f"Color palette: cream white, forest green #1C3A28, gold #C9A84C. "
        f"Style: either hyperrealistic product/object cinematography OR smooth geometric animation with minimal shapes. "
        f"Concept inspired by: {short}. "
        f"No text on screen. No faces. No voice. No sound needed. "
        f"Slow smooth camera movement or gentle geometric motion. "
        f"Luxury brand aesthetic, editorial quality, 4K. "
        f"Feel: sophisticated, confident, minimal — like a premium fashion or architecture brand reel."
    )


def generate_video(post_text: str, output_filename: str = "reel.mp4") -> str:
    """
    Генерирует вертикальное видео 9:16 через Veo 3.
    Возвращает путь к файлу.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = generate_video_prompt(post_text)
    output_path = OUTPUT_DIR / output_filename

    log.info(f"[Veo3] Генерирую видео: {prompt[:80]}...")

    operation = client.models.generate_videos(
        model=MODEL,
        prompt=prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio="9:16",
            duration_seconds=8,
            number_of_videos=1,
        ),
    )

    # Ждём завершения (обычно 1-3 минуты)
    max_wait = 300  # 5 минут максимум
    waited = 0
    while not operation.done:
        time.sleep(15)
        waited += 15
        operation = client.operations.get(operation)
        log.info(f"[Veo3] Ожидаю... {waited}с")
        if waited >= max_wait:
            raise TimeoutError("Veo 3: превышено время ожидания")

    if not operation.response or not operation.response.generated_videos:
        raise RuntimeError("Veo 3: видео не сгенерировано")

    video = operation.response.generated_videos[0]
    video_bytes = client.files.download(file=video.video)
    with open(output_path, "wb") as f:
        f.write(video_bytes)

    log.info(f"[Veo3] Видео сохранено: {output_path}")
    return str(output_path)


def cleanup_video(path: str):
    p = Path(path)
    if p.exists():
        p.unlink()
