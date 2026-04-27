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
import hashlib
import logging
import asyncio
import threading
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import openai

from config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
import ideas_history

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
            await show_next_post(update, context)
            return
        await update.message.reply_text(
            "Отправь видеофайл или напиши *пропустить видео*", parse_mode="Markdown"
        )
        return

    # Режим ожидания медиа (картинки или видео)
    if mode == "waiting_for_image":
        await update.message.reply_text(
            "Отправь картинку или видео, а не текст."
        )
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

def _idea_hash(text: str) -> str:
    """Короткий стабильный id идеи для callback_data."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:10]


def _ensure_ideas_dict(state: dict) -> dict:
    """Нормализует state['ideas'] в dict {hash: idea}.

    Если в состоянии лежит старый list (например, от ещё не перезапущенного
    планировщика main.py), конвертирует его в dict и сохраняет state.
    """
    raw = state.get("ideas") or {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        result: dict = {}
        for idea in raw:
            if not isinstance(idea, dict):
                continue
            title = idea.get("idea", "")
            angle = idea.get("angle", "")
            idea_id = _idea_hash(title + angle)
            result[idea_id] = idea
        state["ideas"] = result
        save_state(state)
        return result
    return {}


def _idea_keyboard(idea_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Используем", callback_data=f"idea:use:{idea_id}"),
        InlineKeyboardButton("⏸ Отложить", callback_data=f"idea:postpone:{idea_id}"),
        InlineKeyboardButton("🗑 Убрать", callback_data=f"idea:remove:{idea_id}"),
    ]])


async def _send_ideas_with_buttons(app: Application, chat_id: int, ideas_dict: dict):
    """Отправляет каждую идею отдельным сообщением с inline-кнопками."""
    await app.bot.send_message(
        chat_id,
        f"📋 *Идеи на сегодня* ({len(ideas_dict)}) — нажми кнопку под каждой:",
        parse_mode="Markdown",
    )
    for idea_id, idea in ideas_dict.items():
        text = (
            f"💡 *{idea['idea']}*\n\n"
            f"_{idea['angle']}_\n\n"
            f"📌 {idea['source']}"
        )
        try:
            await app.bot.send_message(
                chat_id,
                text,
                parse_mode="Markdown",
                reply_markup=_idea_keyboard(idea_id),
            )
        except Exception as e:
            log.warning(f"Не удалось отправить идею {idea_id}: {e}")


async def send_daily_ideas(app: Application, chat_id: int):
    """Запускает новое исследование и отправляет идеи пользователю с кнопками."""
    await app.bot.send_message(chat_id, "🔍 Ищу свежие идеи из российских и зарубежных источников...")

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

    # Превращаем список в dict {hash: idea}, отбрасываем дубли по истории
    ideas_dict: dict = {}
    for idea in ideas:
        if ideas_history.is_blocked(idea.get("idea", "")):
            log.info(f"Идея отфильтрована (used/postponed/removed): {idea.get('idea','')[:60]}")
            continue
        idea_id = _idea_hash(idea.get("idea", "") + idea.get("angle", ""))
        ideas_dict[idea_id] = idea

    if not ideas_dict:
        await app.bot.send_message(
            chat_id,
            "Все найденные идеи уже были предложены раньше. Попробуй /research позже.",
        )
        return

    state = load_state()
    state["ideas"] = ideas_dict
    state["chat_id"] = chat_id
    # mode НЕ переключаем — кнопки работают независимо от режима
    save_state(state)

    await _send_ideas_with_buttons(app, chat_id, ideas_dict)


async def _generate_post_for_idea(idea: dict) -> str:
    """Генерирует текст поста по идее (синхронный generate_post в executor)."""
    from content import generate_post

    draft_topic = {
        "name": "Из исследования",
        "description": "",
        "prompt_hint": f"{idea['idea']}. {idea['angle']}",
        "image_style": "hyperrealistic product photography, cream and forest green palette, luxury aesthetic",
    }
    return await asyncio.get_running_loop().run_in_executor(
        None, lambda: generate_post(draft_topic)
    )


async def handle_idea_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки под идеями."""
    query = update.callback_query
    await query.answer()

    try:
        _, action, idea_id = query.data.split(":", 2)
    except ValueError:
        return

    state = load_state()
    ideas_dict = _ensure_ideas_dict(state)

    idea = ideas_dict.get(idea_id)
    if not idea:
        try:
            await query.edit_message_text("⚠️ Идея устарела (новое исследование уже запущено).")
        except Exception:
            pass
        return

    title = idea.get("idea", "")

    if action == "remove":
        ideas_history.mark_removed(title, title)
        ideas_dict.pop(idea_id, None)
        state["ideas"] = ideas_dict
        save_state(state)
        try:
            await query.edit_message_text(f"🗑 *Убрано навсегда:* {title}", parse_mode="Markdown")
        except Exception:
            pass
        return

    if action == "postpone":
        ideas_history.mark_postponed(title, title)
        ideas_dict.pop(idea_id, None)
        state["ideas"] = ideas_dict
        save_state(state)
        try:
            await query.edit_message_text(f"⏸ *Отложено:* {title}\n\n_(вернётся в выдачу позже)_", parse_mode="Markdown")
        except Exception:
            pass
        return

    if action == "use":
        try:
            await query.edit_message_text(f"🎨 *Генерирую пост:* {title}", parse_mode="Markdown")
        except Exception:
            pass
        try:
            post_text = await _generate_post_for_idea(idea)
        except Exception as e:
            log.exception("Ошибка генерации поста")
            await context.bot.send_message(query.message.chat.id, f"❌ Ошибка генерации: {e}")
            return

        ideas_history.mark_used(title, title)

        # Перечитываем state — за время генерации он мог измениться
        state = load_state()
        ideas_dict = _ensure_ideas_dict(state)
        ideas_dict.pop(idea_id, None)
        state["ideas"] = ideas_dict

        posts = state.get("pending_posts", [])
        posts.append({"idea": title, "post_text": post_text})
        state["pending_posts"] = posts

        # Если бот сейчас не показывает пост — переключаемся и показываем новый
        was_idle = state.get("mode") != "approving_post"
        if was_idle:
            state["mode"] = "approving_post"
            state["current_post_index"] = len(posts) - 1
        save_state(state)

        chat_id = query.message.chat.id

        if was_idle:
            await _show_post_to_chat(context.application, chat_id)
        else:
            await context.bot.send_message(
                chat_id,
                f"📬 Пост *«{title}»* добавлен в очередь ({len(posts) - state.get('current_post_index', 0)} ждут).",
                parse_mode="Markdown",
            )


async def _show_post_to_chat(app: Application, chat_id: int):
    """Показывает текущий pending пост по chat_id (без объекта Update)."""
    state = load_state()
    posts = state.get("pending_posts", [])
    idx = state.get("current_post_index", 0)

    if idx >= len(posts):
        state["mode"] = "idle"
        save_state(state)
        await app.bot.send_message(chat_id, "✅ Все посты обработаны!")
        return

    post = posts[idx]
    final_text = f"{post['post_text']}\n\nНапиши мне → @Nzamba\nhttps://sevrugin.pro"
    image_path = post.get("preview_image")
    video_path = post.get("preview_video")

    has_image = image_path and Path(image_path).exists()
    has_video = video_path and Path(video_path).exists()

    approval_text = (
        f"📝 *Пост {idx+1}/{len(posts)}* — {post.get('idea', '')}\n\n{final_text}\n\n"
        f"*ок* / *да* / *го* — публикую\n"
        f"*пропустить* — следующий\n"
        f"Или напиши правки — переделаю и покажу снова (можно несколько раз)"
    )

    if has_video or has_image:
        state["mode"] = "approving_post"
        save_state(state)

        for attempt in range(3):
            try:
                if has_video:
                    with open(video_path, "rb") as vid:
                        await app.bot.send_video(chat_id, video=vid)
                else:
                    with open(image_path, "rb") as photo:
                        await app.bot.send_photo(chat_id, photo=photo)
                break
            except Exception as e:
                if attempt == 2:
                    log.warning(f"Не удалось отправить медиа после 3 попыток: {e}")
                else:
                    await asyncio.sleep(2)

        for attempt in range(3):
            try:
                await app.bot.send_message(chat_id, approval_text, parse_mode="Markdown")
                break
            except Exception as e:
                if attempt == 2:
                    log.warning(f"Не удалось отправить текст поста после 3 попыток: {e}")
                else:
                    await asyncio.sleep(2)
    else:
        from content import generate_image_prompt
        draft_topic = {"image_style": "hyperrealistic product photography, cream and forest green palette, luxury aesthetic"}
        image_prompt = await asyncio.get_running_loop().run_in_executor(
            None, lambda: generate_image_prompt(draft_topic, final_text)
        )
        state["mode"] = "waiting_for_image"
        state["pending_posts"] = posts
        save_state(state)

        await app.bot.send_message(
            chat_id,
            f"📝 *Пост {idx+1}/{len(posts)}* — {post.get('idea', '')}\n\n{final_text}",
            parse_mode="Markdown",
        )
        await app.bot.send_message(
            chat_id,
            f"🎨 *Промпт для картинки* — вставь в gpt-image-2:\n\n`{image_prompt}`\n\n"
            f"Сгенерируй и отправь картинку или видео сюда.",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )


async def show_next_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает следующий пост на согласование (обёртка для message-контекста)."""
    await _show_post_to_chat(context.application, update.effective_chat.id)


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
    """Пользователь прислал видео — для поста или для Shorts/Reels."""
    state = load_state()
    mode = state.get("mode")

    if mode not in ("waiting_for_video", "waiting_for_image", "approving_post"):
        return

    if update.message.video:
        file = await update.message.video.get_file()
    elif update.message.document:
        file = await update.message.document.get_file()
    else:
        return

    save_path = str(Path(__file__).parent / f"temp_video_{uuid.uuid4().hex[:8]}.mp4")
    await update.message.reply_text("💾 Сохраняю видео...")
    await file.download_to_drive(save_path)

    if mode == "waiting_for_video":
        # Видео для YouTube Shorts / Instagram Reels после публикации поста
        state["pending_video"] = save_path
        save_state(state)
        await update.message.reply_text(
            "🎬 Видео получено!\n\n"
            "Напиши *публикую видео* — залью в YouTube Shorts + Instagram Reels\n"
            "Или *пропустить видео* — удалю",
            parse_mode="Markdown"
        )

    elif mode in ("waiting_for_image", "approving_post"):
        # Видео как превью поста (вместо картинки)
        posts = state.get("pending_posts", [])
        idx = state.get("current_post_index", 0)
        posts[idx]["preview_video"] = save_path
        posts[idx].pop("preview_image", None)  # убираем картинку если была
        state["pending_posts"] = posts
        save_state(state)
        await show_next_post(update, context)


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

    body = post['post_text']
    tg_text  = f"{body}\n\nНапиши мне → @Nzamba\nhttps://sevrugin.pro"
    ig_text  = f"{body}\n\nНапиши мне → @sevrugin_pro"
    fb_text  = f"{body}\n\nsevrugin.pro"
    x_text   = f"{body}\n\nsevrugin.pro"
    preview_image = post.get("preview_image")
    preview_video = post.get("preview_video")
    # для превью в боте используем тг-версию
    final_text = tg_text

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

        await step("📤", "Telegram",   lambda: post_telegram(tg_text, preview_image, preview_video))
        await step("📸", "Instagram",  lambda: post_social(ig_text, preview_image, preview_video, ["instagram"]))
        await step("👥", "Facebook",   lambda: post_social(fb_text, preview_image, preview_video, ["facebook"]))
        await step("🐦", "X",          lambda: post_social(x_text,  preview_image, preview_video, ["x"]))

        await status_msg.edit_text(_build_progress(results, "📝 Блог (генерирую статью ~30 сек)..."))
        try:
            from blog_publisher import publish_to_blog
            blog_url = await asyncio.get_running_loop().run_in_executor(None, lambda: publish_to_blog(final_text))
            results["Блог"] = ("✅", blog_url)
        except Exception as e:
            results["Блог"] = ("❌", str(e))
        await status_msg.edit_text(_build_progress(results))

        for media_file in filter(None, [preview_image, preview_video]):
            try:
                Path(media_file).unlink(missing_ok=True)
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
        await show_next_post(update, context)
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
    """Показать уже полученные сегодня идеи (с кнопками). НЕ запускает новое исследование."""
    state = load_state()
    state["owner_chat_id"] = update.effective_chat.id
    save_state(state)

    state = load_state()
    ideas_dict = _ensure_ideas_dict(state)

    if not ideas_dict:
        await update.message.reply_text(
            "Сегодня идей пока нет. Напиши /research чтобы запустить новое исследование."
        )
        return

    await _send_ideas_with_buttons(context.application, update.effective_chat.id, ideas_dict)


async def cmd_research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запустить новое исследование вручную."""
    state = load_state()
    state["owner_chat_id"] = update.effective_chat.id
    save_state(state)
    await send_daily_ideas(context.application, update.effective_chat.id)


async def cmd_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущий или следующий пост из очереди (даже если mode=idle)."""
    state = load_state()
    posts = state.get("pending_posts", [])
    idx = state.get("current_post_index", 0)

    if not posts or idx >= len(posts):
        await update.message.reply_text("Очередь постов пуста.")
        return

    # Принудительно переключаемся в режим согласования
    state["mode"] = "approving_post"
    save_state(state)
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
    app.add_handler(CommandHandler("research", cmd_research))
    app.add_handler(CommandHandler("show", cmd_show))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CallbackQueryHandler(handle_idea_callback, pattern=r"^idea:"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    log.info("Бот запущен.")
    app.run_polling(bootstrap_retries=-1)


if __name__ == "__main__":
    main()
