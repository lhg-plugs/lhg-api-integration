"""坏用例：API 对接代码的典型反模式集合（冒烟测试用，每条埋点对应一条审计规则）。"""
import requests

API_KEY = "sk-testkey1234567890abcdef"
BASE = "http://api.example.com/v1"

HEADERS = {
    "Authorization": "Bearer abcdefgh12345678",
    "Content-Type": "application/json",
}

print("using key:", API_KEY)


def fetch_users():
    resp = requests.get(BASE + "/users", params={"api_key": API_KEY, "q": "x"}, verify=False)
    return resp.json()


def fetch_orders():
    retries = 3
    for _ in range(retries):
        r = requests.post("https://api.example.com/v1/orders", headers=HEADERS)
        if r.status_code == 200:
            return r.json()
    raise Exception(resp.text)


def poll_status():
    while True:
        r = requests.get("https://api.example.com/v1/status", headers=HEADERS)
        print(r.text)


def fetch_all_pages():
    page = 1
    all_items = []
    while page <= 100:
        r = requests.get(BASE + "/items", headers=HEADERS)
        all_items.extend(r.json())
        page += 1
    return all_items


def risky_call():
    try:
        return requests.get(BASE + "/risky", headers=HEADERS).json()
    except:
        pass
