# Контентные рубрики и расписание постинга
# Каждая рубрика выходит в определённые дни недели
# 0=понедельник, 1=вторник, 2=среда, 3=четверг, 4=пятница, 5=суббота, 6=воскресенье

TOPICS = [
    {
        "id": "anatomy",
        "name": "Анатомия ролика",
        "days": [0, 3],  # понедельник, четверг
        "description": "Разбор реального рекламного ролика: что сработало в сценарии, почему попало в аудиторию, какой приём использован",
        "prompt_hint": "Выбери известный российский или мировой рекламный ролик и разбери его с точки зрения сценария и идеи. Объясни, почему он работает (или не работает).",
        "image_style": "dark cinematic still frame from a TV commercial, professional advertising photography",
    },
    {
        "id": "client_tips",
        "name": "Ликбез для заказчика",
        "days": [1, 4],  # вторник, пятница
        "description": "Практические советы для предпринимателей, которые заказывают рекламу: как не облажаться, что важно, о чём никто не предупреждает",
        "prompt_hint": "Напиши практичный совет для предпринимателя, который хочет заказать рекламный ролик. Разрушь мифы или предупреди о типичной ошибке.",
        "image_style": "professional business meeting, client and creative director discussing ad campaign, dark moody lighting",
    },
    {
        "id": "case",
        "name": "Кейс под ключ",
        "days": [2],  # среда
        "description": "История одного рекламного проекта: задача клиента, идея сценария, процесс, результат",
        "prompt_hint": "Опиши гипотетический или реальный кейс создания рекламного ролика для бизнеса. Задача клиента → идея → решение → результат.",
        "image_style": "behind the scenes of video production, camera crew filming advertisement, professional studio setup",
    },
    {
        "id": "ai_ads",
        "name": "AI в рекламе",
        "days": [5],  # суббота
        "description": "Честный разбор AI-инструментов для видео и рекламы: что реально работает, что маркетинговый булшит",
        "prompt_hint": "Разбери конкретный AI-инструмент для создания видео или рекламы (Sora, Runway, Kling, HeyGen и др.). Честно — что умеет, что нет, когда стоит использовать.",
        "image_style": "futuristic AI video generation interface, neon blue and dark background, technology concept",
    },
    {
        "id": "script_live",
        "name": "Сценарий за стеклом",
        "days": [6],  # воскресенье
        "description": "Процесс написания сценария в реальном времени: черновики, решения, объяснение выборов",
        "prompt_hint": "Покажи процесс написания сценария рекламного ролика: от брифа до финального варианта. Объясни ключевые решения.",
        "image_style": "copywriter writing script at desk, papers and notes scattered, dramatic side lighting, dark moody",
    },
    {
        "id": "digest",
        "name": "Реклама в эфире",
        "days": [],  # раз в 2 недели — управляется вручную через main.py
        "description": "Дайджест лучшей рекламы недели: 3-5 роликов с авторским комментарием",
        "prompt_hint": "Составь дайджест из 3-4 интересных рекламных кампаний или роликов этой недели. Короткий авторский комментарий к каждому.",
        "image_style": "collage of TV screens showing different advertisements, dark background, editorial style",
    },
    {
        "id": "experience",
        "name": "25 лет на одном рынке",
        "days": [],  # 2 раза в месяц — управляется вручную через main.py
        "description": "Личные истории и наблюдения из 25 лет в рекламе: как менялся рынок, необычные клиенты, уроки",
        "prompt_hint": "Расскажи историю или наблюдение из многолетней работы в рекламе. Личный опыт, который невозможно нагуглить.",
        "image_style": "vintage advertising studio, film reels and storyboards, nostalgic warm tones mixed with modern dark aesthetic",
    },
]

# Быстрый поиск рубрики по дню недели
def get_topic_for_today(weekday: int):
    for topic in TOPICS:
        if weekday in topic["days"]:
            return topic
    return None

# Быстрый поиск рубрики по id
def get_topic_by_id(topic_id: str):
    for topic in TOPICS:
        if topic["id"] == topic_id:
            return topic
    return None
