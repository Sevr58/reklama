import json, requests, sys
from pathlib import Path
env = {}
for l in open('/home/sevr/projects/Reklama/.env'):
    if l.startswith('TELEGRAM_BOT_TOKEN='): env['t'] = l.split('=',1)[1].strip().strip('"\'')
chat = json.load(open('/home/sevr/projects/Reklama/bot_state.json'))['owner_chat_id']
api = f"https://api.telegram.org/bot{env['t']}"
out = Path(__file__).parent / 'out'
jpgs = sorted(out.glob('*.jpg'))
media, files = [], {}
for i, p in enumerate(jpgs):
    k = f"f{i}"; files[k] = open(p, 'rb')
    m = {"type": "photo", "media": f"attach://{k}"}
    if i == 0: m["caption"] = "ЖК «Чаадаев» — раскадровки 10 вариантов, 20 с. ★ — рекомендованные: 1 «Окно» и 5 «Шаги». Полное качество — в PDF ниже."
    media.append(m)
r = requests.post(api + "/sendMediaGroup", data={"chat_id": chat, "media": json.dumps(media, ensure_ascii=False)}, files=files, timeout=300)
print("album", r.status_code, r.json().get("ok"), r.json().get("description"))
pdf = out / "Чаадаев_раскадровки_10_вариантов.pdf"
r = requests.post(api + "/sendDocument", data={"chat_id": chat, "caption": "Раскадровки в полном качестве (PDF, 10 страниц)"}, files={"document": open(pdf, 'rb')}, timeout=300)
print("pdf", r.status_code, r.json().get("ok"), r.json().get("description"))
