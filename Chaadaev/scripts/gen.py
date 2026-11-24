import sys, os, json, base64, requests
from pathlib import Path
env = {}
for l in open('/home/sevr/projects/Reklama/.env'):
    if '=' in l and not l.startswith('#'):
        k, v = l.strip().split('=', 1); env[k] = v.strip().strip('"\'')
KEY = env['GEMINI_API_KEY']
STYLE = (" Cinematic storyboard frame, soft pencil sketch with light muted watercolor wash in dark forest green, mint and warm amber tones, "
         "clean professional film storyboard style, 16:9, no text, no letters, no logos, no watermark.")
def gen(prompt, out, model="imagen-4.0-generate-001"):
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict",
        headers={"x-goog-api-key": KEY, "Content-Type": "application/json"},
        json={"instances": [{"prompt": prompt + STYLE}], "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}}, timeout=120)
    if r.status_code != 200:
        return f"ERR {r.status_code} {r.text[:300]}"
    p = r.json().get("predictions")
    if not p: return f"EMPTY {r.text[:300]}"
    Path(out).write_bytes(base64.b64decode(p[0]["bytesBase64Encoded"])); return "ok"
if __name__ == "__main__":
    print(gen(sys.argv[1], sys.argv[2]))
