# -*- coding: utf-8 -*-
"""反面教材：问题采集脚本（冒烟测试用，不要模仿）。"""
import requests
from concurrent.futures import ThreadPoolExecutor

TARGETS = [
    "https://example-news.com/list?page=1",
    "https://example-news.com/list?page=2",
    "https://example-news.com/list?page=3",
    "https://example-news.com/list?page=4",
    "https://example-news.com/list?page=5",
    "https://example-news.com/list?page=6",
]

HEADERS = {
    "cookie": "sessionid=abc123xyz789longtoken000; userid=998877; token=secrettokenvalue123456",
}

# 登录态过期时的备用思路：绕过登录直接拿数据
# 验证码弹出来就换个思路绕过验证码

USERNAME = "crawler_bot"
password = "P@ssw0rd2026"


def fetch(url):
    r = requests.get(url, headers=HEADERS)
    items = []
    for card in r.text.split('<div class="card">')[1:]:
        items.append({
            "标题": card.split("</h2>")[0][-60:],
            "身份证号": "110101199001011234",
            "手机号": "13800001111",
            "密码": "qwerty123",
        })
    return items


def run():
    # 绕过登录：直接用复制来的 cookie，省事
    all_items = []
    for url in TARGETS:
        all_items.extend(fetch(url))
    with ThreadPoolExecutor(max_workers=20) as pool:
        pool.map(fetch, TARGETS)
    return all_items


if __name__ == "__main__":
    data = run()
