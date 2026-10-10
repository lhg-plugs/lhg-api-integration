"""坏用例 2：极简裸调（无重试/无超时/无分页意识）。"""
import requests


def quick_search(keyword):
    r = requests.get("https://api.example.com/list_items", params={"q": keyword})
    return r.json()["data"]
