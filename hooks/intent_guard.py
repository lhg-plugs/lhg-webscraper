#!/usr/bin/env python3
"""lhg-webscraper 硬门：检测用户请求中的登录绕过 / CAPTCHA 绕过 / 付费墙绕过意图。

触发：UserPromptSubmit（用户每次提交请求时）。命中红线关键词时输出告警，
提醒执行者按 lhg-scraper-compliance 第 6 节拒绝，不提供变通方案。

逃生方式（按推荐度排序）：
  1. 改写请求为合规采集需求（只采公开数据），重新提交（推荐）。
  2. 紧急情况：LHG_WS_HOOKS_OFF=1（环境变量，当前会话有效）关闭本检查。
  3. /plugin disable lhg-webscraper（整个插件停用，hooks 不再触发）。

设计原则：
  - 快速放行非目标事件：无命中时零输出、exit 0。
  - 内部出错（输入解析失败等）fail-open 直接放行，不骚扰用户。
  - 本 hook 只做提醒（UserPromptSubmit 不支持拦截），真正的拒绝由执行
    agent 按 skill 规范完成。
  - 零第三方依赖。
"""

import json
import os
import re
import sys

# 红线意图关键词：任一命中即告警
RED_PATTERNS = [
    (re.compile(r"绕过.{0,8}(登录|验证码|验证|人机|付费墙|会员|订阅|反爬)"), "绕过意图"),
    (re.compile(r"(bypass|circumvent|get around).{0,30}(login|captcha|paywall|verification|anti-scraping)", re.I), "bypass intent"),
    (re.compile(r"破解.{0,8}(验证码|验证|登录|付费墙)"), "破解意图"),
    (re.compile(r"(2captcha|anti-?captcha|打码平台|自动打码)"), "打码平台"),
    (re.compile(r"(盗用|借用|复用).{0,8}(cookie|登录态|账号|会话)"), "盗用登录态"),
    (re.compile(r"模拟登录"), "模拟登录"),
    (re.compile(r"(伪装|假装).{0,8}(搜索引擎|爬虫|googlebot|bingbot)", re.I), "伪装身份"),
]


def main() -> int:
    # 逃生开关
    if os.environ.get("LHG_WS_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # 输入解析失败：fail-open

    prompt = payload.get("prompt", "") or ""
    if not prompt:
        return 0

    hits = []
    for pat, label in RED_PATTERNS:
        m = pat.search(prompt)
        if m:
            hits.append((label, m.group(0)[:40]))

    if not hits:
        return 0  # 非目标事件：快速放行

    lines = [
        "合规告警（lhg-webscraper）：检测到疑似绕过意图，请先按 "
        "lhg-scraper-compliance 做合规评估：",
        "",
    ]
    for label, sample in hits:
        lines.append("- [%s] …%s…" % (label, sample))
    lines += [
        "",
        "本插件只采集公开可访问的数据，不绕过登录、付费墙、验证码。",
        "如属误判（如讨论合规边界本身），可设置 LHG_WS_HOOKS_OFF=1 后重试。",
        "确认红线后请按 skill 第 6 节标准话术拒绝，不提供变通方案。",
    ]
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(lines),
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
