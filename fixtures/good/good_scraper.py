# -*- coding: utf-8 -*-
"""正面示例：合规采集脚本（冒烟测试用）。"""
import logging
import time

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("good_scraper")

BASE_URL = "https://example-news.com"
LIST_URL = BASE_URL + "/list?page={page}"
UA = "lhg-webscraper-demo/1.0 (contact: demo@example.com; 仅采集公开列表页)"
REQUEST_INTERVAL = 1.5  # 秒：默认限流间隔 ≥1s


def check_robots(domain):
    """合规预检：读目标站 robots.txt，确认目标路径允许采集。"""
    url = "https://%s/robots.txt" % domain
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        allowed = "Disallow: /list" not in resp.text
    except Exception as exc:  # noqa: BLE001 - 拉取失败走保守策略
        logger.warning("robots.txt 拉取失败，按保守策略继续：%s", exc)
        return True
    logger.info("robots.txt 预检：/list 路径%s", "允许" if allowed else "禁止")
    return allowed


def fetch_with_retry(url, tries=3):
    """带指数退避的重试：429/5xx 最多重试 3 次。"""
    for attempt in range(tries):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": UA},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.text
            logger.warning("非 200 响应：%s -> %s", url, resp.status_code)
        except Exception as exc:  # noqa: BLE001
            logger.warning("请求异常（第 %d 次）：%s %s", attempt + 1, url, exc)
        time.sleep(2 ** attempt)
    logger.error("重试耗尽，放弃：%s", url)
    return ""


def parse_cards(html):
    items = []
    for card in html.split('<div class="card">')[1:]:
        title = card.split("</h2>")[0][-60:].strip()
        if title:
            items.append({"标题": title})
    return items


def run(max_pages=3):
    if not check_robots("example-news.com"):
        logger.error("robots.txt 禁止采集，任务终止")
        return []
    seen = set()  # 去重键：标题
    results = []
    for page in range(1, max_pages + 1):
        url = LIST_URL.format(page=page)
        html = fetch_with_retry(url)
        for item in parse_cards(html):
            if item["标题"] not in seen:
                seen.add(item["标题"])
                results.append(item)
        logger.info("第 %d 页完成，累计 %d 条", page, len(results))
        time.sleep(REQUEST_INTERVAL)  # 限流：每次请求后休眠
    logger.info("采集结束，共 %d 条", len(results))
    return results


if __name__ == "__main__":
    run()
