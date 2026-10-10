---
description: 采集代码体检：跑确定性审计脚本（robots/限流/UA/敏感字段），输出分级报告，blocker 拦截。
argument-hint: [采集代码目录] [--fix]
---

# /lhg-webscraper:audit —— 采集代码体检

用户输入在 `$ARGUMENTS` 中：`[采集代码目录]`，`--fix` 表示自动修显而易见的 warning。

## 合规声明

> **合规声明**：本体检只审计**你自己的采集代码**是否合规（有没有 robots 检查、有没有限流、有没有碰敏感字段），不审计目标站、不提供绕过建议。发现绕过登录/验证码的代码模式将判 blocker 并要求删除。

## 流程（加载 lhg-scraper-compliance 第 5 节清单）

### 1. 跑脚本

```
python3 <插件目录>/scripts/audit/webscraper_audit.py --target <目录> --format text
```

记下 blocker / warning / nit 的数量与明细。

### 2. 分级处理

- **blocker**（必须修）：缺 robots.txt 合规检查、含登录/验证码绕过意图、采集身份证/密码类字段、无超时设置
- **warning**（修或豁免）：无请求限流、UA 缺失、并发过高、硬编码目标站凭证
- **nit**（顺手修）：无日志、无重试、魔法数字

### 3. 输出报告

结论只能是"通过 / 不通过"，blocker 不清零不许说通过。为清零改脚本规则算作弊，不许。

## 硬规则

- 审计脚本本身不许联网"验证"目标站可爬性——合规结论来自 robots.txt 与 ToS 文本，不是"试一下能不能爬"。
- 发现绕过类代码：要求删除，不接受"加个注释说明"作为修复。
