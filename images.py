import openai
import requests
import os
from config import OPENAI_API_KEY

client = openai.OpenAI(api_key=OPENAI_API_KEY)


def generate_image(prompt: str, save_path: str = "temp_image.png") -> str:
    """
    Генерирует изображение через DALL-E 3 и сохраняет локально.
    Возвращает путь к файлу.
    """
    full_prompt = f"{prompt}. Dark, cinematic, professional. No text, no watermarks."

    response = client.images.generate(
        model="dall-e-3",
        prompt=full_prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url

    # Скачиваем изображение локально
    img_response = requests.get(image_url)
    with open(save_path, "wb") as f:
        f.write(img_response.content)

    return save_path


def cleanup_image(path: str):
    """Удаляет временный файл изображения."""
    if os.path.exists(path):
        os.remove(path)
