"""
Контент-завод Севрюгин
======================
Запусти один раз — скрипт будет работать в фоне
и публиковать посты по расписанию.

Использование:
  python main.py             — запустить планировщик (работает постоянно)
  python main.py test        — сгенерировать и опубликовать пост прямо сейчас (для теста)
  python main.py digest      — опубликовать рубрику "Реклама в эфире" вручную
  python main.py experience  — опубликовать "25 лет на одном рынке" вручную
"""

import sys
import time
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from topics import get_topic_for_today, get_topic_by_id
from content import generate_post, generate_image_prompt, polish_draft, adapt_for_platform, client as claude_client
from poster import post_telegram, post_social
from media_finder import extract_ad_reference, find_youtube_video, download_thumbnail
from blog_publisher import publish_to_blog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# Время публикации (по Москве)
POST_HOUR = 10
POST_MINUTE = 0


def _parse_drafts(text: str) -> list[tuple[int, str]]:
    """
    Разбирает файл черновиков на отдельные идеи.
    Пропускает идеи помеченные [✓].
    Возвращает список (номер_строки, текст_идеи).
    """
    import re
    result = []
    for match in re.finditer(r'^(\d+)\.\s+(.+?)(?=\n\d+\.|\Z)', text, re.MULTILINE | re.DOTALL):
        number = int(match.group(1))
        content = match.group(2).strip()
        if content.startswith("[✓]"):
            log.info(f"Пропускаю идею {number} — уже опубликована")
            continue
        result.append((number, content))
    return result


def _mark_done_in_file(draft_path: str, number: int):
    """Помечает идею с заданным номером как [✓] в файле."""
    import re
    with open(draft_path, encoding="utf-8") as f:
        text = f.read()
    # Добавляем [✓] сразу после "N. "
    updated = re.sub(
        rf'^({number}\.\s+)(?!\[✓\])',
        rf'\1[✓] ',
        text,
        flags=re.MULTILINE
    )
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(updated)


def _queue_for_approval(post_text: str, image_path: str, label: str):
    """Ставит готовый пост в очередь бота на согласование и уведомляет пользователя.

    Не перезаписывает чужие режимы (выбор идей, ожидание медиа, согласование текущего поста).
    Если пользователь занят — пост просто кладётся в очередь, об этом приходит уведомление,
    забрать его можно командой /show.
    """
    import requests as req
    from bot import load_state, save_state
    from config import TELEGRAM_BOT_TOKEN

    state = load_state()
    chat_id = state.get("owner_chat_id")

    pending = state.get("pending_posts", [])
    pending.append({
        "idea": label,
        "post_text": post_text,
        "preview_image": image_path,
    })
    state["pending_posts"] = pending

    current_mode = state.get("mode")
    if current_mode in ("approving_post", "waiting_for_image", "waiting_for_video"):
        # Пользователь уже что-то решает — не перебиваем, просто добавляем в очередь
        was_busy = True
    else:
        # Свободен (idle / selecting_ideas / нет режима) — переключаем на показ
        was_busy = False
        state["mode"] = "approving_post"
        state["current_post_index"] = len(pending) - 1

    save_state(state)

    if not chat_id:
        log.warning("owner_chat_id не задан — пост добавлен в очередь без уведомления")
        return

    if was_busy:
        notice = (
            f"📬 *+1 пост в очереди:* {label}\n"
            f"Сейчас ты занят — закончи текущее действие, пост покажется автоматически.\n"
            f"Или напиши /show чтобы посмотреть очередь сейчас."
        )
        try:
            req.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": notice, "parse_mode": "Markdown"},
                timeout=30,
            )
        except Exception as e:
            log.warning(f"Не удалось отправить уведомление об очереди: {e}")
        log.info(f"Пост добавлен в очередь (mode={current_mode}): {label}")
        return

    # Свободен — присылаем картинку и текст на согласование
    final_text = f"{post_text}\n\nНапиши мне → @Nzamba\nhttps://sevrugin.pro"

    if image_path:
        try:
            with open(image_path, "rb") as photo:
                req.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": chat_id},
                    files={"photo": photo},
                    timeout=30,
                )
        except Exception as e:
            log.warning(f"Не удалось отправить картинку: {e}")

    caption = (
        f"📝 *{label}*\n\n{final_text}\n\n"
        f"Напиши *ок* — опубликую\n"
        f"Напиши *пропустить* — следующий\n"
        f"Или напиши правки — переделаю"
    )
    req.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": caption, "parse_mode": "Markdown"},
        timeout=30,
    )
    log.info(f"Пост отправлен на согласование: {label}")


def _publish_single_draft(draft_text: str):
    """Полирует одну идею → картинка → ставит в очередь на согласование."""

    log.info(f"Идея: {draft_text[:80]}...")
    post_text = polish_draft(draft_text)
    log.info(f"Текст готов ({len(post_text)} симв.)")

    image_path = None
    youtube_url = None

    try:
        search_query = extract_ad_reference(post_text, claude_client)
        if search_query:
            video = find_youtube_video(search_query)
            if video:
                image_path = download_thumbnail(video)
                youtube_url = video["url"]
    except Exception as e:
        log.warning(f"Ошибка с медиа: {e}")

    if youtube_url:
        post_text = f"{post_text}\n\n▶️ {youtube_url}"

    _queue_for_approval(post_text, image_path, "Черновик")


def publish_draft(draft_path: str = "draft.txt"):
    """Читает черновик, разбивает на идеи и публикует пост на каждую."""

    with open(draft_path, encoding="utf-8") as f:
        raw = f.read().strip()

    if not raw:
        log.error("Файл draft.txt пустой.")
        return

    drafts = _parse_drafts(raw)

    if not drafts:
        log.info("Нет новых идей для публикации (все уже отмечены [✓]).")
        return

    log.info(f"Найдено новых идей: {len(drafts)}")

    for i, (number, draft_text) in enumerate(drafts, 1):
        log.info(f"\n{'='*50}")
        log.info(f"[{i}/{len(drafts)}] Идея #{number}")
        log.info('='*50)
        _publish_single_draft(draft_text)
        _mark_done_in_file(draft_path, number)
        log.info(f"Идея #{number} помечена как [✓]")
        if i < len(drafts):
            log.info("Пауза 10 сек...")
            time.sleep(10)

    log.info(f"\nГотово! Опубликовано постов: {len(drafts)}")


def publish_post(topic_id: str = None):
    """Основная функция: генерирует контент и публикует."""

    # Определяем рубрику
    if topic_id:
        topic = get_topic_by_id(topic_id)
    else:
        weekday = datetime.now().weekday()
        topic = get_topic_for_today(weekday)

    if not topic:
        log.info("Сегодня постов нет по расписанию.")
        return

    log.info(f"Генерирую пост: {topic['name']}")

    # Генерируем текст
    post_text = generate_post(topic)
    log.info(f"Текст готов ({len(post_text)} симв.)")

    # Ищем YouTube-превью (бесплатно). Картинку пользователь сгенерирует вручную в AI Studio.
    image_path = None
    youtube_url = None

    try:
        search_query = extract_ad_reference(post_text, claude_client)
        if search_query:
            log.info(f"Ищу YouTube-ролик: {search_query}")
            video = find_youtube_video(search_query)
            if video:
                log.info(f"Найдено: {video['title']} → {video['url']}")
                image_path = download_thumbnail(video)
                youtube_url = video["url"]
    except Exception as e:
        log.warning(f"Ошибка с медиа: {e}")

    if youtube_url:
        post_text = f"{post_text}\n\n▶️ {youtube_url}"

    _queue_for_approval(post_text, image_path, topic["name"])
    log.info("Пост отправлен на согласование.")


def send_ideas_sync():
    """Запускает исследование и отправляет идеи с inline-кнопками через Bot API."""
    import hashlib
    import requests as req
    from researcher import run_research
    from config import TELEGRAM_BOT_TOKEN
    from bot import load_state, save_state
    import ideas_history

    state = load_state()
    chat_id = state.get("owner_chat_id")
    if not chat_id:
        log.warning("owner_chat_id не задан — запусти /myid в боте")
        return

    api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    def send(text, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        req.post(f"{api}/sendMessage", json=payload, timeout=30)

    send("🔍 Ищу свежие идеи из российских и зарубежных источников...")

    try:
        ideas = run_research()
    except Exception as e:
        send(f"❌ Ошибка исследования: {e}")
        return

    if not ideas:
        send("Не удалось найти идеи сегодня.")
        return

    # Фильтруем по истории + готовим dict {hash: idea}
    ideas_dict = {}
    for idea in ideas:
        if ideas_history.is_blocked(idea.get("idea", "")):
            log.info(f"Идея отфильтрована: {idea.get('idea','')[:60]}")
            continue
        idea_id = hashlib.md5(
            (idea.get("idea", "") + idea.get("angle", "")).encode("utf-8")
        ).hexdigest()[:10]
        ideas_dict[idea_id] = idea

    if not ideas_dict:
        send("Все найденные идеи уже были предложены раньше. Попробуй /research позже.")
        return

    state["ideas"] = ideas_dict
    # mode НЕ переключаем — кнопки работают независимо
    save_state(state)

    send(f"📋 *Идеи на сегодня* ({len(ideas_dict)}) — нажми кнопку под каждой:")

    for idea_id, idea in ideas_dict.items():
        text = (
            f"💡 *{idea['idea']}*\n\n"
            f"_{idea['angle']}_\n\n"
            f"📌 {idea['source']}"
        )
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Используем", "callback_data": f"idea:use:{idea_id}"},
                {"text": "⏸ Отложить",   "callback_data": f"idea:postpone:{idea_id}"},
                {"text": "🗑 Убрать",     "callback_data": f"idea:remove:{idea_id}"},
            ]]
        }
        send(text, reply_markup=keyboard)

    log.info(f"Идеи отправлены пользователю: {len(ideas_dict)}")


def run_scheduler():
    """Запускает планировщик — публикует пост каждый день в POST_HOUR:POST_MINUTE."""
    scheduler = BlockingScheduler(timezone="Europe/Moscow")

    scheduler.add_job(
        publish_post,
        trigger="cron",
        hour=POST_HOUR,
        minute=POST_MINUTE,
        id="daily_post"
    )

    # Исследование — каждый день в 9:00
    scheduler.add_job(
        send_ideas_sync,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_research"
    )

    log.info(f"Планировщик запущен. Посты в {POST_HOUR:02d}:{POST_MINUTE:02d}, идеи в 09:00 МСК")
    log.info("Нажми Ctrl+C чтобы остановить.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Планировщик остановлен.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "test":
            log.info("=== ТЕСТОВЫЙ ЗАПУСК ===")
            publish_post("anatomy")

        elif command == "draft":
            # Публикация из черновика
            draft_file = sys.argv[2] if len(sys.argv) > 2 else "draft.txt"
            publish_draft(draft_file)

        elif command in ("digest", "experience"):
            # Ручная публикация редких рубрик
            publish_post(command)

        else:
            print(f"Неизвестная команда: {command}")
            print(__doc__)
    else:
        run_scheduler()
