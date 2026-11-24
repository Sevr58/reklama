# «СДЕЛАНО» — Промты Seedance 2.5

## Клип 1 — «Кран, полку, карниз» · v1 (2026-11-23)
Старт: `refs_ours/K1_v3.jpg` (Start frame). Генерим 5 с, в монтаж ~2,6 с (0,0–2,6), хвост 2,6–5,0 — запас.
Голос в Seedance не генерим: «Кран, полку, карниз…» пишем в студии под картинку.

```
START FRAME: the attached image is the exact first frame. Keep the camera position, framing, light, hands, pen, notebook, mug and tools exactly as in it.

SETTING: present day, a bright winter day, a modern apartment. A man (only his hands, forearms and the soft out-of-focus edge of his right shoulder are visible, never his face) sits at a light-oak table and reads through his handwritten to-do list in a spiral notebook. A thin plain gold wedding band on the ring finger of his RIGHT hand. Light-blue chambray shirt sleeves rolled up.

THE NOTEBOOK TEXT IS LOCKED: the blue handwritten Russian words «Список дел:», «Починить кран», «Повесить полку», «Прикрутить карниз» and the four small empty circles stay exactly the same in every frame — no letter changes, morphs, moves or disappears. The fourth circle stays empty, no words are written after it. The only new marks in the whole clip are three short underlines.

SHOT 1 (0–5s), one continuous shot: over-the-shoulder, high angle about 50 degrees, 40mm lens, focus on the pen tip and the handwriting, very slow steady dolly-in of about 3 percent over the whole clip, no other camera movement.
0–0.4s: the right hand lifts the pen tip a few millimetres off the paper and moves it to the left, to the beginning of the word «кран» on the first task line.
0.4–1.0s: the pen tip touches the paper and draws one short straight blue underline left to right, directly under the word «кран» only, the length of that word; the pen lifts at the end of the word.
1.0–1.6s: the hand moves down one line and draws one short straight blue underline left to right directly under the word «полку» only; the pen lifts.
1.6–2.3s: the hand moves down one more line and draws one short straight blue underline left to right directly under the word «карниз» only, pressing a little harder; the pen lifts.
2.3–5s: the pen hovers just above the paper next to «карниз», the hand rests still but alive — a small natural breath in the forearm, a slight relaxing of the fingers; the left hand stays flat on the lower left corner of the notebook the whole time.
End state: three neat blue underlines under «кран», «полку», «карниз», all text unchanged, the fourth circle empty, the pen hovering by the third line.

Movement is calm, real-time and natural, a man thinking while reading his list — no fast or jerky motion, no slow motion.

LIGHT: the only light source is low winter sunlight from an unseen window on the LEFT, outside the frame. Hard, warm, crisp sunbeam diagonally across the table and the page, crisp shadows of the hand and pen falling to the right, thin diagonal mullion shadows on the tabletop at upper left. The hand's shadow moves with the hand. Fine dust particles drift slowly in the sunbeam, a thin wisp of steam rises from the coffee mug in the background. Light does not flicker or change.

LOOK: photorealistic, real cinema footage, ARRI Alexa 35, Kodak Vision3 250D feel, natural skin texture with pores and fine hairs, real paper texture, shallow depth of field with creamy bokeh on the mug and tools, fine film grain, warm natural grading.

SOUND: no dialogue, no voice, no music. Quiet apartment room tone, three soft ballpoint scratches on paper, one on each underline.
```

Негатив:
```
face, head, extra hands, extra fingers, deformed hands, ring on the left hand, changing text, morphing letters, new words, writing in the fourth line, ticks or check marks, crossing out words, scribbles, underline under the wrong word, long lines across the page, text moving, paper warping, distorted text, subtitles, watermark, flicker, light changes, camera shake, handheld, zoom, cut, slow motion, fast motion, cartoon, CGI look, plastic skin, low resolution, voice, speech, music
```

## Клип 1 · v2 (2026-11-23) — то же, что v1, плюс референс `@char_misha` (лист с кольцом на правой руке)
Отличия от v1: блок REFERENCES (лист только для рук, кожи, рубашки, кольца; лица нет), в SETTING — `@char_misha`, в End state — кольцо, в негатив добавлены `neck, rings on both hands`. Полный текст выдан в чат 2026-11-23.
Если голова лезет в кадр или рукав «осветляется» — генерировать без листа (v1).

## Решение 2026-11-23: кольцо убираем совсем
Лист без кольца — `refs_ours/char_misha_v3_noring.png`. На К1 v3 кольцо на правой руке: локально стереть чисто не вышло (палец в фокусе, кольцо пересекает контур) → правка в Nano Banana «remove the ring», затем сверка текста. Клип 1 → v3 (без кольца), полный текст выдан в чат.

## Клип 1 — итог по фильтру (2026-11-23)
С `@char_misha` (лист с реалистичным лицом) Higgsfield ответил «Protected content detected · Credits refunded». Без листа, только `@k1` (тегом, поля Start frame в Higgsfield нет) — сгенерировалось. Вывод (предположение): листы с лицом в референсы Seedance не грузим, лицо даём через стартовый кадр.
Первый кадр задаётся строкой «@k1 is the first frame of the video…».

## Клип 2 — лицо, досада · v1 (2026-11-23)
Стартовый кадр `@k2` — генерация в Nano Banana по листу Миши (промт в `04_кадры.md`). Seedance: 5 с, в монтаж ~2 с; рот закрыт, голос жены из студии. Полный текст выдан в чат.

## Клип 1 — результат v1 (2026-11-23) → `clips/clip1_v1.mp4`
854×480, 24 fps, 5,04 с. Черты под «кран/полку/карниз» точно, текст стабилен, тень переплёта на столе, наезд ~15–20 %. Темп медленнее: черты ~1,0/2,2/3,2 с → в монтаж брать 0,8–3,6 с.
Нужно перегенерировать в 1080p (в Higgsfield выставить разрешение), тем же промтом. Последний кадр для «4-й строки» — из версии 1080p.

## Клип 2 · v2 (2026-11-23)
Добавлены блоки FOCUS (лицо Миши в резкости весь клип, без rack focus) и WOMAN IN THE BACKGROUND (оптически размыта 85 мм f/2, но реальная: вес, ткань, пряди, живые движения; не пластик/манекен/призрак). Эмоция: взгляд замирает → поднимается к ней → брови сходятся, «доходит» → выдох носом → губы сжаты, уголок в сторону («ну конечно, ещё одно»), без злости. Полный текст выдан в чат. Если жена «лезет» в резкость — сократить блок WOMAN до двух фраз.

## Клип 2 — результат v1 (2026-11-23) → `clips/clip2_v1.mp4` (480p)
Евгений: Миша не реалистичный, жена не «говорит». Разбор: переигрывание (8 микродвижений в промте → 5 гримас), косой взгляд «без поворота головы» (моя формулировка), 480p сглаживает кожу, стартовый K2 слишком «золотой и идеальный», жене не дана реплика текстом.
Решение: (1) правка K2 в Nano Banana — реальная кожа, меньше золота/насыщенности, плёночная оптика; (2) Seedance v3 — блок PERFORMANCE (одна реакция, на дыхании, голова поворачивается ~15°), жена говорит "Дорогой, и розетку не забудь!" текстом + кивок и жест лопаткой; (3) 1080p. Полный текст выдан в чат. Запасной путь — тот же кадр в Kling.

## Клип 2 — результат v2 (2026-11-23) → `clips/clip2_v2.mp4` (480p) — РАБОЧИЙ по игре
Стартовый кадр приземлён в Nano Banana, промт v3 (PERFORMANCE, реплика жены текстом). Миша живой, одна реакция (голова ~15°), жена поворачивается и указывает лопаткой. Цвет нейтральный.
Минусы: жёсткий солнечный луч пропал (свет мягкий) — расходится с клипом 1, решать цветокором на монтаже; губы Миши чуть приоткрыты на 2,5–3,5 с; 480p → перегенерировать в 1080p тем же промтом. В монтаж ~0,9–3,9 с (3 с вместо 2) — пересчитать хронометраж.

## Клип 3 — макро «Розетка!» · v1 (2026-11-23)
Старт `@k3` — Nano Banana по К4 (макро 100 мм, «Розетка» без «!», перо справа над бумагой, скользящий свет слева). Seedance 4 с: перо с нажимом ставит палку и точку «!». В монтаж ~0,4–2,4 с под «Успеть бы до праздников…». Полный текст обоих промтов выдан в чат. Если буквы плывут — «!» рисовать в AE.

## Клип 3 — результат v1 → `clips/clip3_v1.mp4` (480p): ничего не происходит
Причина: Евгений сгенерировал сразу из К4, где «!» уже есть; Seedance выдумал страницу (над «Розеткой» стала «полку»).
Исправлено: «!» стёрт локально → `frames/K4_rozetka_noexcl.png`; старт клипа — кроп 960×540 ×2 → `frames/K3_macro_start_crop.png` (отправлен в ТГ). Промт v2 — перо ставит палку и точку «!», точка = финальная точка кадра. Полный текст выдан в чат.

## Клип 3 · v3 (2026-11-24)
v2 (общий план → наезд → перо к «Розетке») провалился: перо заново писало «Розетка», макро не вышло.
v3 = промт v1 (макро 100 мм, @k3 как референс, клип сразу в макро) + блок «THE WORD IS ALREADY WRITTEN», действие: палка «!» с нажимом → точка-удар. Старт: кадр без «!» (скриншот Евгения `frames/K3_start_v2.png` или кроп `frames/K3_macro_start_crop.png`). Полный текст выдан в чат.

## Клип 3 · v4 (2026-11-24)
v3 (макро строит сам Seedance) поставил «!» прямо на слове — 3 генерации впустую. Вывод: место метки на тексте словами не задать; задаёт первый кадр.
v4: первый кадр — кроп `frames/K3_macro_start_crop.png` (перо уже над пустым местом после «Розетка»), короткий промт: перо опускается «straight down at its current position», палка + точка. Одна генерация.
План Б, если промах: знак «!» проявлять в AE маской за пером (подходит clip3_v1, где «!» уже нарисован и перо подходит к нему).

## План 4 · галочки (2026-11-24)
Seedance со статики @k4: пустые кружки, рука поднимает ручку. Галочки #156534 рисуются в AE (4 шт., шаг ~0,3–0,45 с, синхрон с «вжиками»).

## План 5 · реакция (2026-11-24)
@k2 (лицо), сдержанное удивление → полуулыбка с закрытыми губами, начинается в глазах; под «Уже сделано!».

## План 6 · переворот страницы (2026-11-24)
Старт `frames/K6_start_v1.png` (Nano Banana по К4): камера у ближнего края блокнота на уровне стола, пружина вдоль ДЛИННОГО ЛЕВОГО края, одна страница (обложка загнута под низ), окно — пересвеченное свечение без рамы. Seedance @k6 4 с: 0–1,2 лист через луч за пружину на стол слева; 1,2–2 рука разглаживает и уходит вправо; 2–4 статика. В монтаж ~0,8 с.
Уроки: «open notebook / spine of a book» → разворот; камера сбоку → пружина сверху; с этой точки виден только оконный фон (кухня за спиной камеры) — Евгений поправил.

## План 7 · фраза (2026-11-24)
Nano Banana по К4: свежая страница, три строки «Ваш список / домашних дел — / наша работа!», живой мужской почерк синей шариковой, место под 3-й строкой для зелёной линии (AE), перевёрнутый лист слева от пружины. Результат `frames/K7_phrase_v1_screenshot.png`, текст проверен побуквенно. Нужен оригинал 2752×1536. Рекомендация: наезд в AE (2 слоя), а не Seedance.

## Музыка · Suno (2026-11-24)
100 BPM (доля 0,6 с → 7,2 с = начало 4-го такта, галочки по восьмым 0,3 с). Евгений попросил комичнее. Итоговый стиль: playful comedic orchestral, на цыпочках (пиццикато, фагот стаккато, вудблок) → вздох засурдиненного тромбона под «Успеть бы…» → весёлый марш (туба, ксилофон, хлопки, кларнет) → «та-да» в конце. Exclude: vocals, humming, circus, kazoo, slide whistle, boing, EDM, sad, fade out. Lyrics — только метатеги [Intro]/[Verse]/[Break]/[Chorus]/[Outro]/[End].

## Превью v1 · разбор (2026-11-24) → `clips/preview_v1.mp4` (1920×1080, 24 fps, 15 с)
Склейки: 0–1,9 руки · 1,9–5,2 лицо+жена · 5,2–7,1 список и галочки · 7,1–8,7 улыбка · 8,7–10,0 переворот · 10,0–11,4 фраза · 11,4–15 пэкшот (лого клиента, 537-111, 8 (8412) · Пенза).
Галочки по кадрам: 5,46 / 5,88 / 6,33 / 6,92 с.
Звук: −7,4 LUFS, true peak +1,1 dBFS (клип); 13,3–15 с почти тишина (~−34 dB).
Замечания (по важности):
1. Громкость → −23 LUFS, пик ≤ −1 dBTP.
2. Галочки стартуют через 0,3 с после склейки, вероятно под «Успеть бы…» (речь ~4,5–5,75 с по уровням, слова не проверены) — нужен «момент дна» 0,3–0,5 с с пустыми кружками после реплики.
3. В плане галочек ручка у «карниз», рука рабочая — галочки читаются как его действие; взять кусок с неподвижной рукой.
4. Ручка на лице серебряная, в остальных планах зелёная — перекрасить в AE или кадрировать.
5. Свет: список — жёсткое солнце, лицо — мягкий серый; цветокор.
6. Фраза 1,4 с против ~2,3 с речи диктора; нет зелёного подчёркивания.
7. Конец музыки — затухание, нужен удар под последнее слово.
8. 24 → 25 fps для эфира.
Ждём от Евгения: дорожку голоса или тайминги «Успеть бы до праздников…» → пересчитать склейки.
