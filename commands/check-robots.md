---
description: robots.txt 合规预检：拉取目标站 robots.txt，解析允许/禁止路径，给出本次采集是否合规的结论。
argument-hint: <目标域名或URL>
---

# /lhg-webscraper:check-robots —— robots.txt 合规预检

用户输入在 `$ARGUMENTS` 中：`<目标域名或URL>`。

## 合规声明

> **合规声明**：本命令只读取目标站公开的 `/robots.txt`（站点主动公示的爬取规则），不做任何绕过动作。robots.txt 只是"君子协定"的一部分，还需同时遵守目标站 ToS 与法律法规。

## 流程

### 1. 拉取与解析

```
python3 <插件目录>/scripts/audit/webscraper_audit.py --check-robots <目标域名> --format text
```

脚本会：请求 `https://<域名>/robots.txt` → 按 RFC 9309 语义解析 User-agent / Disallow / Allow / Crawl-delay / Sitemap。

### 2. 输出预检报告

```markdown
## robots.txt 预检：<域名>
- 拉取状态：成功 / 失败（失败原因）
- 适用规则组：User-agent: * （或最匹配的一组）
- 本次目标路径 <路径>：✅ 允许 / ❌ 禁止
- Crawl-delay：<n> 秒（无则按默认 ≥1 秒）
- Sitemap：<有/无>（有则优先从 sitemap 拿 URL 清单，减少无效请求）
- 结论：可继续方案设计 / 建议更换采集路径 / 停止
```

### 3. 例外处理

- robots.txt 拉取失败（404/超时）：视为"无明确禁止"，但仍按默认限流执行，并在报告里注明"未取到 robots.txt，已按保守策略执行"。
- 目标路径被 Disallow：直接判本次采集不可行，不提供"换个 UA 绕过去"之类的建议。

## 硬规则

- 预检结论为"禁止"时，不许继续走 `/lhg-webscraper:scrape` 的后续步骤。
- 不许把 robots.txt 的禁止路径解读为"技术上可绕过"——禁止就是禁止。
