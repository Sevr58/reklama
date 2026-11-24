import json, requests, sys
sys.path.insert(0, sys.argv[1]); from msgs import M1, M2
tok = [l.split('=', 1)[1].strip().strip('"\'') for l in open('/home/sevr/projects/Reklama/.env') if l.startswith('TELEGRAM_BOT_TOKEN=')][0]
chat = json.load(open('/home/sevr/projects/Reklama/bot_state.json'))['owner_chat_id']
for m in (M1, M2):
    print(len(m), end=' ')
    r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", data={"chat_id": chat, "text": m, "parse_mode": "HTML"}, timeout=60)
    print(r.status_code, r.json().get("ok"), r.json().get("description"))
