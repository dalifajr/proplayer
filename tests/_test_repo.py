import requests, re

cookies = {
    '_octo': 'GH1.1.1668559833.1770055924',
    'cpu_bucket': 'lg',
    'tz': 'Asia%2FJakarta',
    '_device_id': 'ac341f0d5b1cd18b66b05d47e566052c',
    'GHCC': 'Required:1-Analytics:1-SocialMedia:1-Advertising:1',
    'color_mode': '%7B%22color_mode%22%3A%22dark%22%7D',
    'user_session': 'x-pJGYTmo5M8EFMoX_lM5VR65HkAsa_q6Mh168DE6hjqQFj3',
    '__Host-user_session_same_site': 'x-pJGYTmo5M8EFMoX_lM5VR65HkAsa_q6Mh168DE6hjqQFj3',
    'logged_in': 'yes',
    'dotcom_user': 'HOZINKING',
    '_gh_sess': 'GGixBMJx4t0vRDRjtjm9zjtL5PZ1Idc7o1fPspHHzXfspl4anenIz1VzVdfEQljk2WNSffK2ih01MzZhzAXxLq2hUGHdP3HdKQTR1LcMf8de5OQ%2FUXViQTZrxeJVPpAtWk5IuRTz1cwIb39Q%2F0%2FG4gqi3UN5euIQWNCRacc26kBOfopsFRsx%2FJkr6tNXMKR2Jjk8Ctl9BUFrgjea3JrfKiMogmazTJh20BUKi3mB1fErilL4dVw43YWbhUU5DV4W98KLyV6q%2Fv8o2%2FMBnuswU4AQVQxO2bcErks7GIqCAYc2CovhCgWVJSLi1Xa71CUi%2F%2F%2BUwFWPeDH7ByU6QpyqWMJix%2B36y69WAPI0HxdtEuTq6dJ1iDY8KJhDbyXisebRgh3TnxKyHm55u7xg5%2BU0%2BjfIy9JOiewadkjZ5bGpyYfeKWprGbUNSJD2fYz1RTSbOx9krcDh7cDPnuqZeB1qVZhddkFsTt2AiNg%2FY%2FwKGeT7H1ia1SMuaIvPHoB5pWsp%2FPZ24M0xplFG4j2Ow7%2FcRmlNOn7DnkUXpVkYiQ0NYOFpCAPNHEhKhklyAumJNhfaKad33cLcSfqwiTfs%2Bcsz73ACqzWbOt6Vb%2BH0yaude5tKutbpdxoWfrn0MdyMz2GeRAyBILPCZQQst8FmOGwZ%2BbSgiZTuvlbRtB4Oo1m1pvSEqXkXarh9Ypreg8%2B%2FcKA8jlEgEjXNNgvfyL9rwKGHGkSpORrIn7dxna8lZCmbKA14i5VeBa4ca0Fn9u9XhQMvTPecpW93nLlCrRuJbZxHMOfzfzmSp7CJsBro%2F7abWs2MSkRuj8da2Bubvbrsm8yhgGESV%2F8QjW1Hr7AOWJxnI6jzipo2NwIANikrCMmlLvxN8JY6GkjTuaE8sLwAVzaerid8i%2BxOm6o8TOsFW%2BsC6Y%2BTLdJ15hhQHNo2HF588R%2F0mxdPx60VXpaqKoVOTtY97rFjilxIGIfv8D0TosxqafCWXmI%3D--DIFe6DKu5%2BEvLkcS--b7DfTKSrd73wNSCQQd6rLQ%3D%3D',
}

s = requests.Session()
s.cookies.update(cookies)
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'})

print("=== GET /new ===")
page = s.get('https://github.com/new', timeout=20)
print('status:', page.status_code)
nonce_m = re.search(r'<meta name="fetch-nonce" content="([^"]+)"', page.text)
nonce = nonce_m.group(1) if nonce_m else None
print('nonce:', nonce)

NONCE_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    'GitHub-Verified-Fetch': 'true',
    'X-Fetch-Nonce': nonce or '',
    'Origin': 'https://github.com',
    'Referer': 'https://github.com/new',
}

def dump(label, r):
    loc = r.headers.get('location', '')
    ct = r.headers.get('content-type', '')
    print(f"\n=== {label} ===")
    print(f"status={r.status_code}  url={r.url}  location={loc}  ct={ct[:40]}")
    if r.status_code in (301, 302, 303):
        print(f"REDIRECT -> {loc}")
        if 'hozinking' in loc.lower():
            print(">>> SUCCESS!")
        return
    if 'json' in ct:
        print("JSON:", r.text[:800])
        try:
            d = r.json()
            redirect = (d.get('data') or {}).get('redirect') or d.get('redirect') or d.get('html_url')
            if redirect:
                print(f">>> SUCCESS - redirect: {redirect}")
        except: pass
    else:
        body = r.text
        if 'Your browser did something unexpected' in body:
            print("=> CSRF error")
        elif r.status_code == 500:
            print("=> 500 server error")
            print("Headers:", {k:v for k,v in r.headers.items() if k.lower().startswith('x-')})
        else:
            stripped = re.sub(r'<[^>]+>', ' ', body)
            stripped = re.sub(r'\s+', ' ', stripped).strip()
            print("Body:", stripped[100:700])
            if 'hozinking' in r.url.lower():
                print(">>> SUCCESS (repo page)!")

# Exact payload from the React repo-creation bundle (tW submit function)
exact = {
    "owner": "HOZINKING",
    "template_repository_id": "",
    "include_all_branches": "0",
    "repository": {
        "name": "test-z-exact-0302b",
        "visibility": "public",
        "description": "",
        "auto_init": "1",
        "license_template": "",
        "gitignore_template": "",
    },
    "metrics": {"submitted_using_v2": True, "elapsed_ms": 3000, "submit_clicked_count": 1},
}

dump("exact payload no-follow", s.post('https://github.com/repositories',
     json=exact, headers=NONCE_HEADERS, timeout=30, allow_redirects=False))

dump("exact payload follow", s.post('https://github.com/repositories',
     json=exact, headers=NONCE_HEADERS, timeout=30, allow_redirects=True))

# Minimal - no metrics
minimal = {
    "owner": "HOZINKING",
    "template_repository_id": "",
    "include_all_branches": "0",
    "repository": {
        "name": "test-z-exact-0302c",
        "visibility": "public",
        "description": "",
        "auto_init": "1",
        "license_template": "",
        "gitignore_template": "",
    },
}
dump("minimal no-follow", s.post('https://github.com/repositories',
     json=minimal, headers=NONCE_HEADERS, timeout=30, allow_redirects=False))
