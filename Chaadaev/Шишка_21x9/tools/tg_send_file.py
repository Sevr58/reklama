import json, requests, sys
tok=[l.split('=',1)[1].strip().strip('"\'') for l in open('/home/sevr/projects/Reklama/.env') if l.startswith('TELEGRAM_BOT_TOKEN=')][0]
chat=json.load(open('/home/sevr/projects/Reklama/bot_state.json'))['owner_chat_id']
p,name,cap=sys.argv[1],sys.argv[2],sys.argv[3]
r=requests.post(f"https://api.telegram.org/bot{tok}/sendDocument",data={'chat_id':chat,'caption':cap},files={'document':(name,open(p,'rb'))},timeout=300)
print(r.status_code,r.json().get('ok'),r.json().get('description'))
