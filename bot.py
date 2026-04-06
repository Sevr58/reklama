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
"""

import re
import json
import logging
import asyncio
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

    # Проверяем — не в режиме ли выбора идей
    state = load_state()
    if state.get("mode") == "selecting_ideas":
        await handle_idea_selection(update, context)
        return
    if state.get("mode") == "approving_post":
        await handle_approval(update, context)
        return

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
        text = await asyncio.get_event_loop().run_in_executor(
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
        "image_style": "dark cinematic professional advertising photography, moody lighting"
    }

    for idea in selected:
        try:
            draft_topic["prompt_hint"] = f"{idea['idea']}. {idea['angle']}"
            post_text = await asyncio.get_event_loop().run_in_executor(
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
    """Показывает следующий пост на одобрение."""
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

    await update.message.reply_text(
        f"📝 *Пост {idx+1}/{len(posts)}* — {post['idea']}\n\n{final_text}\n\n"
        f"Напиши *ок* — опубликую\n"
        f"Напиши *пропустить* — следующий\n"
        f"Или напиши правки — переделаю",
        parse_mode="Markdown"
    )


async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает одобрение/отклонение поста."""
    text = update.message.text.strip().lower()
    state = load_state()
    posts = state.get("pending_posts", [])
    idx = state.get("current_post_index", 0)
    post = posts[idx]

    signature = "Напиши мне → @Nzamba\nsevrugin.pro"
    final_text = f"{post['post_text']}\n\n{signature}"

    if text in ("ок", "ok", "окей", "давай", "публикуй", "да"):
        # Публикуем
        await update.message.reply_text("🚀 Публикую...")
        try:
            report = await asyncio.get_event_loop().run_in_executor(
                None, lambda: _publish_approved_post(final_text)
            )
            await update.message.reply_text(f"Опубликовано:\n{report}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")

        state["current_post_index"] = idx + 1
        save_state(state)
        await show_next_post(update, context)

    elif text in ("пропустить", "skip", "нет", "не надо"):
        state["current_post_index"] = idx + 1
        save_state(state)
        await show_next_post(update, context)

    else:
        # Если пользователь прислал длинный текст — это его собственный вариант, использовать как есть
        # Если короткая правка — применить к оригиналу через polish_draft
        if len(text) > 100:
            await update.message.reply_text("✅ Беру твой текст как основу.")
            posts[idx]["post_text"] = text
            state["pending_posts"] = posts
            save_state(state)
            await show_next_post(update, context)
        else:
            await update.message.reply_text("✍️ Переделываю...")
            from content import polish_draft
            corrected = await asyncio.get_event_loop().run_in_executor(
                None, lambda: polish_draft(f"{post['post_text']}\n\nПравки: {text}")
            )
            posts[idx]["post_text"] = corrected
            state["pending_posts"] = posts
            save_state(state)
            await show_next_post(update, context)


def _publish_approved_post(text: str) -> str:
    """Синхронная публикация одобренного поста. Возвращает отчёт."""
    from poster import post_telegram, post_social
    from content import adapt_for_platform
    from images import generate_image, cleanup_image
    from content import generate_image_prompt

    draft_topic = {"image_style": "dark cinematic professional advertising photography"}

    image_path = None
    try:
        image_prompt = generate_image_prompt(draft_topic, text)
        image_path = generate_image(image_prompt)
    except Exception as e:
        log.warning(f"Изображение не сгенерировано: {e}")

    results = ["✅ Telegram"]

    post_telegram(text, image_path)

    for platform in ["instagram", "facebook"]:
        try:
            post_social(adapt_for_platform(text, platform), image_path, [platform])
            results.append(f"✅ {platform.capitalize()}")
        except Exception as e:
            results.append(f"❌ {platform.capitalize()}: {e}")
            log.warning(f"[{platform}] Ошибка: {e}")

    if image_path:
        cleanup_image(image_path)

    return "\n".join(results)


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
    pending = [d for d in _read_drafts() if not d[2]]
    if not pending:
        await update.message.reply_text("Нет новых черновиков.")
        return
    await update.message.reply_text(f"🚀 Публикую {len(pending)} черновиков...")
    try:
        await asyncio.get_event_loop().run_in_executor(None, publish_draft)
        await update.message.reply_text("✅ Готово!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запустить исследование вручную."""
    await send_daily_ideas(context.application, update.effective_chat.id)


# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("publish", cmd_publish))
    app.add_handler(CommandHandler("ideas", cmd_ideas))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    log.info("Бот запущен.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
