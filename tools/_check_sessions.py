import json, requests
with open("sessions.json") as f:
    sessions = json.load(f)
for sess in sessions:
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    for part in sess["cookies"].split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            s.cookies.set(k.strip(), v.strip(), domain="github.com", path="/")
    r = s.get("https://github.com/settings/profile", timeout=10, allow_redirects=False)
    status = "VALID" if r.status_code == 200 else f"EXPIRED ({r.status_code})"
    print(f"{sess['label']}: {status}")
