"""
Генерирует и публикует по одному посту из каждой рубрики.
Между постами пауза 10 секунд, чтобы не спамить канал.

Запуск: python generate_all.py
"""

import time
import logging
from main import publish_post
from topics import TOPICS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

PAUSE_SECONDS = 10

if __name__ == "__main__":
    log.info(f"Запускаю генерацию {len(TOPICS)} постов...")

    for i, topic in enumerate(TOPICS, 1):
        log.info(f"\n{'='*50}")
        log.info(f"[{i}/{len(TOPICS)}] Рубрика: {topic['name']}")
        log.info('='*50)

        publish_post(topic["id"])

        if i < len(TOPICS):
            log.info(f"Пауза {PAUSE_SECONDS} сек перед следующим постом...")
            time.sleep(PAUSE_SECONDS)

    log.info("\nВсе посты опубликованы!")
