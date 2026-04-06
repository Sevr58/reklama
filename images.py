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

    full_prompt = (
        f"{prompt}. "
        f"Color palette: cream white #F8F5F0, dark forest green #1C3A28, gold #C9A84C. "
        f"Style: either hyperrealistic product photography with natural side lighting OR clean geometric abstract composition. "
        f"Elegant, minimal, sophisticated — luxury brand aesthetic. "
        f"No text, no words, no logos, no watermarks, no human faces. Square 1:1."
    )

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
