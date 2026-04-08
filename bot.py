"""
Telegram-бот Севрюгин.

Функции:
1. Принимает текстовые и голосовые черновики → сохраняет в draft.txt
2. Утром присылает 6 идей из иностранных источников на выбор
3. По выбранным идеям генерирует посты → показывает на одобрение → публикует

Команды:
  /list    — показать черновики
  /publish — опубликовать черновики
  /myid    — показать твой Telegram ID
  /ideas   — запустить исследование вручную прямо сейчас
  /restart — перезапустить бота (сбросить зависший режим)
"""

import os
import re
import sys
import uuid
import json
import logging
import asyncio
import threading
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import openai

from config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

DRAFT_FILE = Path(__file__).parent / "draft.txt"
STATE_FILE = Path(__file__).parent / "bot_state.json"

openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Состояния диалога
SELECTING_IDEAS = 1
APPROVING_POST = 2


# ─── Хранилище состояния ──────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── Работа с черновиками ─────────────────────────────────────────────────────

def _next_number() -> int:
    if not DRAFT_FILE.exists():
        return 1
    text = DRAFT_FILE.read_text(encoding="utf-8")
    numbers = re.findall(r'^(\d+)\.', text, re.MULTILINE)
    return max((int(n) for n in numbers), default=0) + 1

def _append_draft(text: str) -> int:
    number = _next_number()
    with open(DRAFT_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{number}. {text.strip()}\n")
    return number

def _read_drafts() -> list[tuple[int, str, bool]]:
    if not DRAFT_FILE.exists():
        return []
    text = DRAFT_FILE.read_text(encoding="utf-8")
    result = []
    for match in re.finditer(r'^(\d+)\.\s+(.+?)(?=\n\d+\.|\Z)', text, re.MULTILINE | re.DOTALL):
        number = int(match.group(1))
        content = match.group(2).strip()
        done = content.startswith("[✓]")
        if done:
            content = content[4:].strip()
        result.append((number, content, done))
    return result


# ─── Транскрипция голосового ──────────────────────────────────────────────────

def _transcribe_voice_sync(file_path: str) -> str:
    with open(file_path, "rb") as audio:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1", file=audio, language="ru"
        )
    return transcript.text


# ─── Обработчики черновиков ───────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        return

    state = load_state()

    mode = state.get("mode")

    # Режим ожидания видео от пользователя
    if mode == "waiting_for_video":
        if text.lower() in ("публикую видео", "видео ок", "публикуй видео", "да"):
            await handle_video_publish(update, context)
            return
        if text.lower() in ("пропустить видео", "удали видео", "нет видео", "skip", "пропустить"):
            v = state.get("pending_video")
            if v:
                from video import cleanup_video
                cleanup_video(v)
                state.pop("pending_video", None)
            state.pop("pending_video_text", None)
            state["mode"] = "idle"
            save_state(state)
            await update.message.reply_text("🗑 Видео пропущено.")
            return
        await update.message.reply_text(
            "Отправь видеофайл или напиши *пропустить видео*", parse_mode="Markdown"
        )
        return

    # Режим ожидания картинки
    if mode == "waiting_for_image":
        await update.message.reply_text(
            "Отправь картинку (фото), а не текст."
        )
        return

    if mode == "selecting_ideas":
        await handle_idea_selection(update, context)
        return
    if mode == "approving_post":
        await handle_approval(update, context)
        return

    # Сохраняем chat_id владельца для main.py
    state["owner_chat_id"] = update.effective_chat.id
    save_state(state)

    number = _append_draft(text)
    await update.message.reply_text(
        f"✅ Идея #{number} сохранена.\n\n/publish — опубликовать\n/list — все идеи"
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙 Расшифровываю...")
    voice_file = await update.message.voice.get_file()
    tmp_path = Path(__file__).parent / "temp_voice.ogg"
    await voice_file.download_to_drive(tmp_path)
    try:
        text = await asyncio.get_running_loop().run_in_executor(
            None, lambda: _transcribe_voice_sync(str(tmp_path))
        )
        number = _append_draft(text)
        await update.message.reply_text(
            f"✅ Записано как идея #{number}:\n\n_{text}_",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


# ─── Утренняя рассылка идей ───────────────────────────────────────────────────

async def send_daily_ideas(app: Application, chat_id: int):
    """Запускает исследование и отправляет идеи пользователю."""
    await app.bot.send_message(chat_id, "🔍 Ищу свежие идеи из иностранных источников...")

    try:
        from researcher import run_research
        ideas = await asyncio.to_thread(run_research)
    except Exception as e:
        log.exception("Ошибка исследования")
        await app.bot.send_message(chat_id, f"❌ Ошибка исследования: {e}")
        return

    if not ideas:
        await app.bot.send_message(chat_id, "Не удалось найти идеи. Попробуй позже или добавь вручную.")
        return

    # Сохраняем идеи в состояние
    state = load_state()
    state["mode"] = "selecting_ideas"
    state["ideas"] = ideas
    state["chat_id"] = chat_id
    save_state(state)

    # Формируем сообщение
    lines = ["📋 *Идеи на сегодня* — выбери номера через запятую:\n"]
    for i, idea in enumerate(ideas, 1):
        lines.append(f"*{i}.* {idea['idea']}\n_{idea['angle']}_\n📌 {idea['source']}\n")

    lines.append("Например: `1, 3, 5` — и я сгенерирую посты по выбранным идеям.")

    await app.bot.send_message(
        chat_id,
        "\n".join(lines),
        parse_mode="Markdown"
    )


async def handle_idea_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь выбрал идеи по номерам."""
    text = update.message.text.strip()
    state = load_state()
    ideas = state.get("ideas", [])

    # Парсим номера
    numbers = [int(n.strip()) for n in re.split(r'[,\s]+', text) if n.strip().isdigit()]
    selected = [ideas[n-1] for n in numbers if 1 <= n <= len(ideas)]

    if not selected:
        await update.message.reply_text("Не понял выбор. Напиши номера через запятую, например: 1, 3")
        return

    await update.message.reply_text(
        f"✅ Выбрано {len(selected)} идей. Генерирую посты..."
    )

    state["mode"] = "approving_post"
    state["pending_posts"] = []
    state["current_post_index"] = 0

    # Генерируем посты для выбранных идей
    from content import generate_post, generate_image_prompt
    from topics import get_topic_by_id

    draft_topic = {
        "name": "Из исследования",
        "description": "",
        "prompt_hint": "",
        "image_style": "hyperrealistic product photography, cream and forest green palette, luxury aesthetic"
    }

    for idea in selected:
        try:
            draft_topic["prompt_hint"] = f"{idea['idea']}. {idea['angle']}"
            post_text = await asyncio.get_running_loop().run_in_executor(
                None, lambda t=draft_topic: generate_post(t)
            )
            state["pending_posts"].append({
                "idea": idea["idea"],
                "post_text": post_text,
            })
        except Exception as e:
            log.warning(f"Ошибка генерации поста: {e}")

    save_state(state)
    await show_next_post(update, context)


async def show_next_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает следующий пост на согласование."""
    state = load_state()
    posts = state.get("pending_posts", [])
    idx = state.get("current_post_index", 0)

    if idx >= len(posts):
        state["mode"] = "idle"
        save_state(state)
        await update.message.reply_text("✅ Все посты обработаны!")
        return

    post = posts[idx]
    signature = "Напиши мне → @Nzamba\nsevrugin.pro"
    final_text = f"{post['post_text']}\n\n{signature}"
    image_path = post.get("preview_image")

    if image_path and Path(image_path).exists():
        # Картинка уже есть (YouTube-превью или загружена вручную) — сразу на согласование
        state["mode"] = "approving_post"
        save_state(state)
        with open(image_path, "rb") as photo:
            await update.message.reply_photo(photo=photo)
        await update.message.reply_text(
            f"📝 *Пост {idx+1}/{len(posts)}* — {post.get('idea', '')}\n\n{final_text}\n\n"
            f"*ок* / *да* / *го* — публикую\n"
            f"*пропустить* — следующий\n"
            f"Или напиши правки — переделаю и покажу снова (можно несколько раз)",
            parse_mode="Markdown"
        )
    else:
        # Нет картинки — просим сгенерировать вручную на AI Studio
        from content import generate_image_prompt
        draft_topic = {"image_style": "hyperrealistic product photography, cream and forest green palette, luxury aesthetic"}
        image_prompt = await asyncio.get_running_loop().run_in_executor(
            None, lambda: generate_image_prompt(draft_topic, final_text)
        )
        state["mode"] = "waiting_for_image"
        state["pending_posts"] = posts
        save_state(state)

        await update.message.reply_text(
            f"📝 *Пост {idx+1}/{len(posts)}* — {post.get('idea', '')}\n\n{final_text}",
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            f"🎨 *Промпт для картинки* — вставь в AI Studio:\n\n`{image_prompt}`\n\n"
            f"[Открыть Google AI Studio](https://aistudio.google.com/generate-image)\n\n"
            f"Сгенерируй и отправь картинку сюда.",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь прислал картинку (фото или файл-изображение) для поста."""
    state = load_state()

    mode = state.get("mode")
    if mode not in ("waiting_for_image", "approving_post"):
        await update.message.reply_text("Картинка получена, но сейчас нет активного поста.")
        return

    try:
        await update.message.reply_text("💾 Сохраняю...")
        save_path = str(Path(__file__).parent / f"temp_image_{uuid.uuid4().hex[:8]}.jpg")

        if update.message.photo:
            # Обычное фото — берём наибольший размер
            file = await update.message.photo[-1].get_file()
        else:
            # Документ (PNG/JPG отправленный как файл)
            file = await update.message.document.get_file()

        await file.download_to_drive(save_path)

        posts = state.get("pending_posts", [])
        idx = state.get("current_post_index", 0)
        posts[idx]["preview_image"] = save_path
        state["pending_posts"] = posts
        save_state(state)

        await show_next_post(update, context)
    except Exception as e:
        log.exception("Ошибка при обработке фото")
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь прислал видео для Shorts/Reels."""
    state = load_state()

    if state.get("mode") != "waiting_for_video":
        return

    await update.message.reply_text("💾 Сохраняю видео...")

    if update.message.video:
        file = await update.message.video.get_file()
    elif update.message.document:
        file = await update.message.document.get_file()
    else:
        return

    save_path = str(Path(__file__).parent / f"temp_video_{uuid.uuid4().hex[:8]}.mp4")
    await file.download_to_drive(save_path)

    state["pending_video"] = save_path
    save_state(state)

    await update.message.reply_text(
        "🎬 Видео получено!\n\n"
        "Напиши *публикую видео* — залью в YouTube Shorts + Instagram Reels\n"
        "Или *пропустить видео* — удалю",
        parse_mode="Markdown"
    )


def _build_progress(results: dict, current: str = "") -> str:
    lines = []
    for label, (icon, detail) in results.items():
        line = f"{icon} {label}"
        if detail:
            line += f" — {detail[:80]}" if len(detail) > 80 else f" — {detail}"
        lines.append(line)
    if current:
        lines.append(current)
    return "\n".join(lines) if lines else "🚀 Публикую..."


async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает одобрение/отклонение поста."""
    text = update.message.text.strip().lower()
    state = load_state()
    posts = state.get("pending_posts", [])
    idx = state.get("current_post_index", 0)
    post = posts[idx]

    signature = "Напиши мне → @Nzamba\nsevrugin.pro"
    final_text = f"{post['post_text']}\n\n{signature}"
    preview_image = post.get("preview_image")

    if text in ("ок", "ok", "окей", "давай", "публикуй", "публикую", "да", "го", "вперед", "вперёд"):
        status_msg = await update.message.reply_text("🚀 Публикую...")

        results = {}  # label -> (ok, detail)

        async def step(emoji: str, label: str, fn):
            try:
                await status_msg.edit_text(_build_progress(results, f"{emoji} {label}..."))
            except Exception:
                pass
            try:
                detail = await asyncio.get_running_loop().run_in_executor(None, fn)
                results[label] = ("✅", str(detail) if detail else "")
            except Exception as e:
                log.error(f"[step:{label}] {e}", exc_info=True)
                results[label] = ("❌", str(e)[:80])
            try:
                await status_msg.edit_text(_build_progress(results))
            except Exception:
                pass

        from poster import post_telegram, post_social

        await step("📤", "Telegram",   lambda: post_telegram(final_text, preview_image))
        await step("📸", "Instagram",  lambda: post_social(final_text, preview_image, ["instagram"]))
        await step("👥", "Facebook",   lambda: post_social(final_text, preview_image, ["facebook"]))
        await step("🐦", "X",          lambda: post_social(final_text, preview_image, ["x"]))

        await status_msg.edit_text(_build_progress(results, "📝 Блог (генерирую статью ~30 сек)..."))
        try:
            from blog_publisher import publish_to_blog
            blog_url = await asyncio.get_running_loop().run_in_executor(None, lambda: publish_to_blog(final_text))
            results["Блог"] = ("✅", blog_url)
        except Exception as e:
            results["Блог"] = ("❌", str(e))
        await status_msg.edit_text(_build_progress(results))

        if preview_image:
            try:
                Path(preview_image).unlink(missing_ok=True)
            except Exception:
                pass

        state["current_post_index"] = idx + 1
        state["pending_video_text"] = final_text
        save_state(state)

        # Отправляем промпт для ручной генерации видео
        from video import generate_video_prompt
        video_prompt = generate_video_prompt(final_text)
        state2 = load_state()
        state2["mode"] = "waiting_for_video"
        save_state(state2)

        await update.message.reply_text(
            f"🎬 *Промпт для видео* — вставь в Veo 3 на AI Studio:\n\n`{video_prompt}`\n\n"
            f"[Открыть Google AI Studio](https://aistudio.google.com)\n\n"
            f"Сгенерируй, скачай и отправь видео сюда.\n"
            f"Или напиши *пропустить видео*.",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    elif text in ("пропустить", "skip", "нет", "не надо"):
        state["current_post_index"] = idx + 1
        save_state(state)
        await show_next_post(update, context)

    else:
        try:
            await update.message.reply_text("✍️ Переделываю...")
        except Exception:
            pass
        from content import polish_draft
        corrected = await asyncio.get_running_loop().run_in_executor(
            None, lambda: polish_draft(f"{post['post_text']}\n\nПравки от автора: {update.message.text.strip()}")
        )
        posts[idx]["post_text"] = corrected
        state["pending_posts"] = posts
        save_state(state)
        await show_next_post(update, context)




async def handle_video_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Публикует видео, загруженное пользователем, в YouTube Shorts + Instagram Reels."""
    state = load_state()
    video_path = state.get("pending_video")
    text = state.get("pending_video_text", "")

    if not video_path or not Path(video_path).exists():
        await update.message.reply_text("Нет загруженного видео. Отправь видеофайл сначала.")
        return

    await update.message.reply_text("🚀 Публикую видео в Shorts/Reels...")
    try:
        from poster import post_video
        from video import cleanup_video
        post_video(text, video_path, ["youtube", "instagram"])
        cleanup_video(video_path)
        state.pop("pending_video", None)
        state.pop("pending_video_text", None)
        state["mode"] = "idle"
        save_state(state)
        await update.message.reply_text("✅ YouTube Shorts + Instagram Reels опубликованы!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


# ─── Команды ──────────────────────────────────────────────────────────────────

async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Твой chat_id: `{update.effective_chat.id}`", parse_mode="Markdown")

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    drafts = _read_drafts()
    if not drafts:
        await update.message.reply_text("Черновиков нет.")
        return
    lines = [("✅" if done else "⏳") + f" {n}. {text[:80]}" for n, text, done in drafts]
    await update.message.reply_text("\n".join(lines))

async def cmd_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from main import publish_draft
    log.info(f"[/publish] вызван, chat_id={update.effective_chat.id}")
    pending = [d for d in _read_drafts() if not d[2]]
    log.info(f"[/publish] черновиков найдено: {len(pending)}")
    if not pending:
        await update.message.reply_text("Нет новых черновиков.")
        return
    await update.message.reply_text(
        f"🎨 Генерирую {len(pending)} пост(ов) из черновиков — пришлю на согласование..."
    )
    # Сохраняем chat_id чтобы main.py мог прислать превью
    state = load_state()
    state["owner_chat_id"] = update.effective_chat.id
    save_state(state)
    try:
        log.info("[/publish] запускаю publish_draft в executor...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, publish_draft)
        log.info("[/publish] publish_draft завершён")
    except Exception as e:
        log.error(f"[/publish] ошибка: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_raw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет черновик на согласование БЕЗ переработки — текст как есть."""
    from main import _queue_for_approval, _mark_done_in_file
    pending = [d for d in _read_drafts() if not d[2]]
    if not pending:
        await update.message.reply_text("Нет новых черновиков.")
        return
    await update.message.reply_text(
        f"📋 Отправляю {len(pending)} черновик(ов) без изменений..."
    )
    state = load_state()
    state["owner_chat_id"] = update.effective_chat.id
    save_state(state)
    for number, draft_text, _ in pending:
        _queue_for_approval(draft_text, None, "Черновик (без правки)")
        _mark_done_in_file(str(DRAFT_FILE), number)
        log.info(f"[/raw] черновик #{number} поставлен в очередь")

async def cmd_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запустить исследование вручную."""
    await send_daily_ideas(context.application, update.effective_chat.id)


async def cmd_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повторно показать текущий пост на согласование."""
    state = load_state()
    if state.get("mode") != "approving_post":
        await update.message.reply_text("Сейчас нет поста на согласовании.")
        return
    await show_next_post(update, context)


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перезапустить бота — сбрасывает зависшие режимы и стартует заново."""
    state = load_state()
    # Разрешаем только владельцу
    owner = state.get("owner_chat_id")
    if owner and update.effective_chat.id != owner:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    state["mode"] = "idle"
    state["notify_restart"] = update.effective_chat.id
    save_state(state)
    await update.message.reply_text("🔄 Перезапускаю бота...")

    def _do_restart():
        import time
        time.sleep(1.5)
        subprocess_args = [sys.executable] + sys.argv
        import subprocess
        subprocess.Popen(subprocess_args)
        os._exit(0)

    threading.Thread(target=_do_restart, daemon=True).start()


# ─── Запуск ───────────────────────────────────────────────────────────────────

LOCK_FILE = Path(__file__).parent / "bot.pid"

def _kill_previous():
    """Убивает предыдущий процесс бота по PID-файлу."""
    if not LOCK_FILE.exists():
        return
    try:
        old_pid = int(LOCK_FILE.read_text().strip())
        if old_pid == os.getpid():
            return
        import psutil
        try:
            p = psutil.Process(old_pid)
            p.kill()
            log.info(f"Убит старый процесс бота PID={old_pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    except Exception:
        pass
    LOCK_FILE.unlink(missing_ok=True)


def _write_pid():
    LOCK_FILE.write_text(str(os.getpid()))


def main():
    _kill_previous()
    _write_pid()

    state = load_state()
    # Сбрасываем только режимы ожидания медиа — approving_post сохраняем
    if state.get("mode") in ("waiting_for_image", "waiting_for_video"):
        log.info(f"Сбрасываю зависший mode='{state['mode']}' → idle")
        state["mode"] = "idle"
        save_state(state)

    async def _on_startup(app: Application):
        state = load_state()
        chat_id = state.pop("notify_restart", None)
        if chat_id:
            save_state(state)
            await app.bot.send_message(chat_id, "✅ Бот перезапущен и готов к работе.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(_on_startup).build()

    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("publish", cmd_publish))
    app.add_handler(CommandHandler("raw", cmd_raw))
    app.add_handler(CommandHandler("ideas", cmd_ideas))
    app.add_handler(CommandHandler("show", cmd_show))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    log.info("Бот запущен.")
    app.run_polling(bootstrap_retries=-1)


if __name__ == "__main__":
    main()
