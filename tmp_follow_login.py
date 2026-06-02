import requests

BASE = "https://dashboard-web-production-d7a0.up.railway.app"
LOGIN_URL = f"{BASE}/accounts/login/"

s = requests.Session()
r = s.get(LOGIN_URL, timeout=20)
r.raise_for_status()

marker = 'name="csrfmiddlewaretoken" value="'
csrf = r.text.split(marker, 1)[1].split('"', 1)[0]

p = s.post(
    LOGIN_URL,
    data={"username": "admin", "password": "1234", "csrfmiddlewaretoken": csrf},
    headers={"Referer": LOGIN_URL},
    allow_redirects=True,
    timeout=20,
)

print("FINAL_URL", p.url)
print("FINAL_STATUS", p.status_code)
print(p.text[:300])
