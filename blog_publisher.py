"""
Публикация постов на сайт sevrugin.pro/blog/

Берёт Telegram-пост, разворачивает в полноценную статью,
создаёт HTML-файл, обновляет blog/index.html и загружает на сервер.
"""

import re
import ftplib
import json
import logging
from datetime import datetime
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY

log = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SITE_DIR = Path("C:/Users/30889/Claude/Site")
BLOG_DIR = SITE_DIR / "blog"

FTP_HOST = "a30889y0.beget.tech"
FTP_USER = "a30889y0_sevrugin"
FTP_PASS = "Sevr1982!!!"

SVG_ARROW = '<svg viewBox="0 0 16 16" fill="none"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'


# ─── Транслитерация для slug ──────────────────────────────────────────────────

TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
    'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
    'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts',
    'ч':'ch','ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'
}

def slugify(text: str) -> str:
    text = text.lower()
    result = ""
    for ch in text:
        result += TRANSLIT.get(ch, ch)
    result = re.sub(r'[^a-z0-9]+', '-', result)
    result = result.strip('-')
    return result[:60]


# ─── Генерация статьи через Claude ───────────────────────────────────────────

def generate_article(post_text: str) -> dict:
    """
    Разворачивает Telegram-пост в полноценную статью для блога.
    Возвращает словарь с полями: title, tag, badge, description, html_content, read_time
    """

    prompt = f"""У меня есть пост из Telegram-канала рекламного продюсера Евгения Севрюгина.
Разверни его в полноценную статью для блога на сайте sevrugin.pro.

Требования:
- Стиль: живой, прямой, с личным опытом — как в исходном посте, но длиннее
- Длина: 600-900 слов
- Структура: введение → 3-5 подзаголовков h2 → заключение
- HTML-теги только внутри <article>: <p>, <h2>, <ul>, <ol>, <li>, <strong>, <div class="highlight">...</div>
- Никакого <html>, <head>, <body> — только содержимое статьи

Верни JSON строго в таком формате (без markdown-обёртки):
{{
  "title": "Заголовок статьи",
  "tag": "Короткий тег (1-2 слова, например: Экспертиза, Кейс, Совет, Тренд)",
  "badge": "Метка для карточки (1 слово, например: Кейс, Гайд, Опыт)",
  "description": "Описание для мета-тега и карточки блога (1-2 предложения, до 160 символов)",
  "html_content": "<p>Текст статьи в HTML...</p>",
  "read_time": 6
}}

Исходный пост:
{post_text}"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Убираем возможные markdown-обёртки
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    return json.loads(raw)


# ─── Создание HTML-файла статьи ───────────────────────────────────────────────

def create_article_html(article: dict, slug: str) -> Path:
    """Создаёт HTML-файл статьи по шаблону."""

    today = datetime.now().strftime("%-d %B %Y").replace(
        "January","января").replace("February","февраля").replace(
        "March","марта").replace("April","апреля").replace(
        "May","мая").replace("June","июня").replace(
        "July","июля").replace("August","августа").replace(
        "September","сентября").replace("October","октября").replace(
        "November","ноября").replace("December","декабря")

    url = f"https://sevrugin.pro/blog/{slug}.html"

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{article['title']} — Севрюгин</title>
  <meta name="description" content="{article['description']}" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{url}" />
  <meta property="og:title" content="{article['title']}" />
  <meta property="og:description" content="{article['description']}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:image" content="https://sevrugin.pro/Sevrugin_logo.png" />
  <meta property="og:type" content="article" />
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{article['title']}",
    "description": "{article['description']}",
    "author": {{ "@type": "Person", "name": "Евгений Севрюгин", "url": "https://sevrugin.pro/" }},
    "publisher": {{ "@type": "Person", "name": "Евгений Севрюгин" }},
    "datePublished": "{datetime.now().strftime('%Y-%m-%d')}",
    "url": "{url}"
  }}
  </script>
  <link rel="icon" type="image/png" href="/Sevrugin_logo.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,300;1,400&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="blog.css" />
</head>
<body>

  <header class="header">
    <div class="container header__inner">
      <a href="/" class="logo">
        <img src="/Sevrugin_logo.png" alt="Севрюгин" class="logo__img" />
      </a>
      <nav class="nav">
        <a href="/#services" class="nav__link">Услуги</a>
        <a href="/#portfolio" class="nav__link">Портфолио</a>
        <a href="/#prices" class="nav__link">Цены</a>
        <a href="/blog/" class="nav__link nav__link--active">Блог</a>
        <a href="/#contact" class="nav__link">Контакт</a>
      </nav>
    </div>
  </header>

  <section class="article-hero">
    <div class="article-hero__inner">
      <span class="article-hero__tag">{article['tag']}</span>
      <h1 class="article-hero__title">{article['title']}</h1>
      <p class="article-hero__desc">{article['description']}</p>
      <div class="article-hero__meta">
        <span>Евгений Севрюгин</span>
        <span>·</span>
        <span>{today}</span>
        <span>·</span>
        <span>{article['read_time']} мин чтения</span>
      </div>
    </div>
  </section>

  <article class="article-wrap">
    <div class="prose">

      {article['html_content']}

      <div class="article-cta">
        <p class="article-cta__title">Готовы обсудить проект?</p>
        <p class="article-cta__desc">Расскажите о задаче — отвечу быстро, без лишних вопросов и навязывания.</p>
        <a href="/#contact" class="btn btn--ghost">Написать</a>
      </div>

      <div class="article-author">
        <img src="/kling_20260201_Image_Reference_Restyle_to_5297_0.png" alt="Евгений Севрюгин" class="article-author__img" />
        <div>
          <div class="article-author__name">Евгений Севрюгин</div>
          <div class="article-author__role">Рекламный продюсер · 25 лет в профессии</div>
        </div>
      </div>

    </div>
  </article>

  <footer class="footer">
    <div class="container">
      <p class="footer__seo">Заказать рекламный ролик под ключ · Рекламный ролик для бизнеса · Видеореклама под ключ</p>
    </div>
    <div class="container footer__inner">
      <a href="/" class="footer__logo logo">
        <img src="/Sevrugin_logo.png" alt="Евгений Севрюгин" class="logo__img" />
      </a>
      <span class="footer__copy">© 2026 Евгений Севрюгин. Все права защищены.</span>
    </div>
  </footer>

</body>
</html>"""

    file_path = BLOG_DIR / f"{slug}.html"
    file_path.write_text(html, encoding="utf-8")
    log.info(f"Статья создана: {file_path}")
    return file_path


# ─── Обновление blog/index.html ───────────────────────────────────────────────

def update_blog_index(article: dict, slug: str):
    """Добавляет карточку новой статьи в начало blog/index.html."""

    index_path = BLOG_DIR / "index.html"
    content = index_path.read_text(encoding="utf-8")

    new_card = f"""
        <a href="/blog/{slug}.html" class="blog-card">
          <div class="blog-card__badge"><span>{article['badge']}</span></div>
          <div class="blog-card__body">
            <p class="blog-card__tag">{article['tag']}</p>
            <h2 class="blog-card__title">{article['title']}</h2>
            <p class="blog-card__desc">{article['description']}</p>
            <div class="blog-card__footer">
              <span class="blog-card__meta">{article['read_time']} мин · Евгений Севрюгин</span>
              <span class="blog-card__link">Читать {SVG_ARROW}</span>
            </div>
          </div>
        </a>
"""

    # Вставляем карточку первой в grid
    updated = content.replace(
        '<div class="blog-grid">',
        '<div class="blog-grid">' + new_card,
        1
    )

    index_path.write_text(updated, encoding="utf-8")
    log.info("blog/index.html обновлён")


# ─── Загрузка на сервер по FTP ────────────────────────────────────────────────

def upload_files(files: list[tuple[Path, str]]):
    """Загружает список (локальный_путь, удалённый_путь) на FTP-сервер."""

    ftp = ftplib.FTP()
    ftp.connect(FTP_HOST, 21, timeout=60)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.set_pasv(True)

    for local_path, remote_path in files:
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path}", f)
        log.info(f"Загружено: {remote_path}")

    ftp.quit()


# ─── Главная функция ──────────────────────────────────────────────────────────

def publish_to_blog(post_text: str):
    """Полный цикл: пост → статья → HTML → сайт."""

    log.info("Генерирую статью для блога...")
    article = generate_article(post_text)
    slug = slugify(article["title"])
    log.info(f"Slug: {slug}")

    article_path = create_article_html(article, slug)
    update_blog_index(article, slug)

    log.info("Загружаю на сервер...")
    upload_files([
        (article_path, f"blog/{slug}.html"),
        (BLOG_DIR / "index.html", "blog/index.html"),
    ])

    log.info(f"Статья опубликована: https://sevrugin.pro/blog/{slug}.html")
    return f"https://sevrugin.pro/blog/{slug}.html"
