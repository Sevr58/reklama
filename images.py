import uuid
import logging
from pathlib import Path

from google import genai
from google.genai import types

from config import GEMINI_API_KEY

log = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "imagen-4.0-generate-001"


def generate_image(prompt: str, save_path: str = None) -> str:
    """
    Генерирует изображение через Google Imagen 4 и сохраняет локально.
    Возвращает путь к файлу.
    """
    if save_path is None:
        save_path = f"temp_image_{uuid.uuid4().hex[:8]}.png"

    full_prompt = f"{prompt}. Dark cinematic professional advertising photography. No text, no watermarks, no logos."

    response = client.models.generate_images(
        model=MODEL,
        prompt=full_prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="1:1",
        ),
    )

    image_data = response.generated_images[0].image.image_bytes
    with open(save_path, "wb") as f:
        f.write(image_data)

    log.info(f"[Imagen4] Изображение сохранено: {save_path}")
    return save_path


def cleanup_image(path: str):
    p = Path(path)
    if p.exists():
        p.unlink()
