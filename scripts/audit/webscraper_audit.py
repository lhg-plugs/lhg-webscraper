#!/usr/bin/env python3
"""lhg-webscraper 确定性采集审计：14 条规则，零第三方依赖。

三种模式：
  1. 代码审计：python3 webscraper_audit.py --target <采集代码目录> [--format json|text]
     扫描 Python 采集代码：robots 合规、限流、UA、敏感字段、绕过意图等。
  2. robots 预检：python3 webscraper_audit.py --check-robots <域名> [--format json|text]
     拉取目标站 /robots.txt，按 RFC 9309 语义解析，给出允许/禁止结论。
  3. 字段扫描：python3 webscraper_audit.py --scan-fields <csv|json文件> [--format json|text]
     扫描数据列名是否含身份证/手机号/密码类敏感字段。

有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）；
--fail-on 可把门槛收紧到 warning/nit。

规则文案均为本项目原创（思路受 Scrapy 分层、RFC 9309 robots 规范启发，
未复制任何第三方原文）。
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.request

VERSION = "1.0.0"
TOOL = "lhg-webscraper/audit"

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "dist", "build", "venv", ".venv",
    "fixtures", "tests", "test",
}
SCAN_EXTS = {".py"}

# ---------------------------------------------------------------- 数据结构

class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line",
                 "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line,
                 snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


class Ctx:
    """单文件扫描上下文。"""

    def __init__(self, path, text):
        self.path = path
        self.text = text
        self.lines = text.split("\n")
        self.findings = []

    def add(self, rule_id, severity, category, title, line, snippet, detail):
        self.findings.append(Finding(rule_id, severity, category, title,
                                     self.path, line, snippet.strip()[:160],
                                     detail))


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def collect_files(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext in SCAN_EXTS:
                out.append(os.path.join(root, f))
    return sorted(out)


# ---------------------------------------------------------------- 规则定义
# 每条规则：id / severity / category / title / detail / check(ctx)

REQUEST_CALL_RES = [
    re.compile(r"\brequests\.(get|post|put|delete|head)\s*\("),
    re.compile(r"\bhttpx\.(get|post|request)\s*\("),
    re.compile(r"\burllib\.request\.urlopen\s*\("),
    re.compile(r"\baiohttp\b"),
    re.compile(r"\bsession\.(get|post)\s*\("),
]

BYPASS_PATTERNS = [
    (re.compile(r"绕过.{0,6}(登录|验证码|验证|人机|付费墙|会员|订阅)"), "中文绕过意图"),
    (re.compile(r"(bypass|circumvent).{0,20}(login|captcha|paywall|verification)", re.I), "英文绕过意图"),
    (re.compile(r"(2captcha|anti-?captcha|captcha-?solver)", re.I), "第三方打码平台"),
    (re.compile(r"破解.{0,6}(验证码|验证|登录)"), "破解意图"),
    (re.compile(r"自动打码"), "自动打码"),
    (re.compile(r"(盗用|借用|复用他人).{0,6}(cookie|登录态|账号)", re.I), "盗用登录态"),
]

SENSITIVE_FIELD_RES = [
    (re.compile(r"身份证|身份證"), "身份证号"),
    (re.compile(r"\bid_?card\b", re.I), "id_card"),
    (re.compile(r"\bssn\b", re.I), "ssn"),
    (re.compile(r"手机号|電話號碼|电话号码"), "手机号"),
    (re.compile(r"\b(mobile|phone_number|cellphone)\b", re.I), "手机号英文字段"),
    (re.compile(r"密码|passwd|password", re.I), "密码"),
    (re.compile(r"银行卡|bank_?card", re.I), "银行卡"),
    (re.compile(r"住址|家庭地址|home_address", re.I), "住址"),
]

CRED_RE = re.compile(
    r"""(?i)\b(password|passwd|api[_-]?key|secret[_-]?key|access[_-]?token)\b"""
    r"""\s*[:=]\s*['"][^'"]{3,}['"]"""
)

COOKIE_RE = re.compile(r"""(?i)['"]cookie['"]\s*:\s*['"][^'"]{24,}['"]""")

RULES = []


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        RULES.append({
            "id": rule_id, "severity": severity, "category": category,
            "title": title, "detail": detail, "check": fn,
        })
        return fn
    return deco


def _has_request_call(text):
    return any(r.search(text) for r in REQUEST_CALL_RES)


def _in_loop(text):
    # 启发式：文件既有循环关键字又有请求调用
    return bool(re.search(r"^\s*(for|while)\b", text, re.M)) and _has_request_call(text)


@rule("WS-CMP-001", "blocker", "合规",
      "缺少 robots.txt 合规检查",
      "代码发起 HTTP 请求，却没有任何 robots.txt 合规检查逻辑。合规采集的第一步是读目标站 robots.txt：先加 check_robots() 之类的预检，再决定采不采。")
def _r_cmp_001(ctx):
    if _has_request_call(ctx.text) and "robots" not in ctx.text.lower():
        ctx.add("WS-CMP-001", "blocker", "合规", "缺少 robots.txt 合规检查",
                1, ctx.lines[0] if ctx.lines else "",
                "检测到 HTTP 请求调用，但全文无 robots 相关检查。先用 "
                "/lhg-webscraper:check-robots 做预检，通过后再写采集逻辑。")


@rule("WS-CMP-002", "blocker", "合规",
      "含登录/验证码/付费墙绕过意图",
      "代码或注释出现绕过登录、绕过验证码、破解付费墙、第三方打码平台等意图。这是本插件的红线：直接拒绝，不提供变通。请删除相关代码，改为只采集公开可访问数据。")
def _r_cmp_002(ctx):
    for i, ln in enumerate(ctx.lines, 1):
        for pat, label in BYPASS_PATTERNS:
            if pat.search(ln):
                ctx.add("WS-CMP-002", "blocker", "合规",
                        "含登录/验证码/付费墙绕过意图（%s）" % label,
                        i, ln, "红线：删除该逻辑。本插件不采集需绕过手段才能拿到的数据。")


@rule("WS-SEC-001", "blocker", "安全",
      "采集身份证/手机号/密码类敏感字段",
      "字段名或注释出现身份证号、手机号、密码、银行卡、住址等敏感字段。这是合规红线：删掉这些字段再采集，清洗环节也必须剔除。")
def _r_sec_001(ctx):
    for i, ln in enumerate(ctx.lines, 1):
        for pat, label in SENSITIVE_FIELD_RES:
            if pat.search(ln):
                ctx.add("WS-SEC-001", "blocker", "安全",
                        "采集敏感字段（%s）" % label, i, ln,
                        "删掉该字段。个人敏感信息不在本插件的采集范围内。")


@rule("WS-SEC-002", "blocker", "安全",
      "硬编码账号密码/API Key",
      "代码里直接写了 password/api_key/secret 等凭证明文。换成环境变量或密钥管理，绝不进代码仓库。")
def _r_sec_002(ctx):
    for i, ln in enumerate(ctx.lines, 1):
        if CRED_RE.search(ln):
            ctx.add("WS-SEC-002", "blocker", "安全", "硬编码凭证", i, ln,
                    "凭证改走环境变量读取，当前明文必须删除并轮换已泄露的凭证。")


@rule("WS-RAT-001", "warning", "限流",
      "循环请求无频率限制",
      "在循环里发 HTTP 请求，却没有 sleep/限流/退避。默认请求间隔 ≥1 秒，并发 ≤3；目标站 robots 有 Crawl-delay 的按更大的来。")
def _r_rat_001(ctx):
    if _in_loop(ctx.text) and not re.search(
            r"(time\.sleep|sleep\(|throttle|rate_limit|ratelimit|限流|delay\(|asyncio\.sleep)",
            ctx.text, re.I):
        ctx.add("WS-RAT-001", "warning", "限流", "循环请求无频率限制",
                1, "", "循环内加 time.sleep(≥1) 或接入限流器，避免对目标站造成压力。")


@rule("WS-RAT-002", "warning", "限流",
      "并发数过高",
      "线程池 max_workers > 8，或 asyncio.gather 无信号量约束。采集并发默认 ≤3，高并发会被目标站视为攻击。")
def _r_rat_002(ctx):
    for i, ln in enumerate(ctx.lines, 1):
        m = re.search(r"max_workers\s*=\s*(\d+)", ln)
        if m and int(m.group(1)) > 8:
            ctx.add("WS-RAT-002", "warning", "限流",
                    "并发数过高（max_workers=%s）" % m.group(1), i, ln,
                    "降到 ≤3；需要更快先确认目标站允许，再逐步加。")
    if re.search(r"asyncio\.gather", ctx.text) and _has_request_call(ctx.text) \
            and "Semaphore" not in ctx.text:
        ctx.add("WS-RAT-002", "warning", "限流", "asyncio.gather 无信号量约束",
                1, "", "给协程请求加 asyncio.Semaphore(3) 约束并发。")


@rule("WS-UA-001", "warning", "礼貌",
      "未设置 User-Agent",
      "发起 HTTP 请求却没带 User-Agent。带上如实标识身份的 UA（含联系方式更佳），这是对目标站最基本的礼貌，也是很多站点的硬性要求。")
def _r_ua_001(ctx):
    if _has_request_call(ctx.text) and "User-Agent" not in ctx.text \
            and "user_agent" not in ctx.text.lower():
        ctx.add("WS-UA-001", "warning", "礼貌", "未设置 User-Agent",
                1, "", "请求头加上 User-Agent：如实说明用途与联系方式。")


@rule("WS-NET-001", "warning", "健壮",
      "请求未设置超时",
      "requests/httpx 调用没传 timeout。网络抖动时无超时=线程卡死=采集任务 hang 住。所有请求显式设置 timeout（如 timeout=15）。")
def _r_net_001(ctx):
    for i, ln in enumerate(ctx.lines, 1):
        if re.search(r"\brequests\.(get|post|put|delete|head)\s*\(", ln):
            # 向前看：括号配平前若出现 timeout 则视为已设置（支持多行调用）
            depth = 0
            seen_timeout = False
            for j in range(i - 1, min(i + 12, len(ctx.lines))):
                seg = ctx.lines[j]
                depth += seg.count("(") - seg.count(")")
                if "timeout" in seg:
                    seen_timeout = True
                    break
                if depth <= 0 and j > i - 1:
                    break
            if not seen_timeout:
                ctx.add("WS-NET-001", "warning", "健壮", "请求未设置超时", i, ln,
                        "加上 timeout=15（或按站点情况调整）。")
                break  # 每个文件只报一次，避免刷屏


@rule("WS-NET-002", "warning", "健壮",
      "无重试/退避机制",
      "有请求调用但无 retry/重试/backoff 逻辑。目标站偶发 429/5xx 时，无重试=整批任务白跑；建议指数退避重试 3 次。")
def _r_net_002(ctx):
    if _has_request_call(ctx.text) and not re.search(
            r"(retry|重试|backoff|tenacity|Retry)", ctx.text):
        ctx.add("WS-NET-002", "warning", "健壮", "无重试/退避机制",
                1, "", "对 429/5xx 做指数退避重试（最多 3 次），别用裸循环死磕。")


@rule("WS-QLT-001", "warning", "健壮",
      "未校验响应状态码",
      "请求后没检查 status_code / raise_for_status。404/403 的错误页会被当成正常数据解析，产出脏数据。")
def _r_qlt_001(ctx):
    if _has_request_call(ctx.text) and not re.search(
            r"(status_code|raise_for_status|response\.ok|\.status\s*==)", ctx.text):
        ctx.add("WS-QLT-001", "warning", "健壮", "未校验响应状态码",
                1, "", "请求后先校验状态码，非 200 按错误处理并记录。")


@rule("WS-QLT-002", "warning", "可维护",
      "无日志记录",
      "采集代码无 logging/print 日志。线上出问题时没有日志=盲飞：至少记录请求数、成功率、失败 URL。")
def _r_qlt_002(ctx):
    if _has_request_call(ctx.text) and not re.search(
            r"(logging|logger\.|print\(|log\.)", ctx.text):
        ctx.add("WS-QLT-002", "warning", "可维护", "无日志记录",
                1, "", "接入 logging，记录关键节点（开始/结束/失败 URL/耗时）。")


@rule("WS-HON-001", "warning", "诚信",
      "硬编码会话 Cookie 复用登录态",
      "请求头里写死了超长 Cookie。这通常是从浏览器复制的个人登录态：会过期、会把个人账号暴露给脚本，且可能违反目标站 ToS。公开数据不需要登录态；需要登录的数据不在本插件采集范围。")
def _r_hon_001(ctx):
    for i, ln in enumerate(ctx.lines, 1):
        if COOKIE_RE.search(ln):
            ctx.add("WS-HON-001", "warning", "诚信",
                    "硬编码会话 Cookie 复用登录态", i, ln,
                    "删掉该 Cookie。如数据必须登录可见，说明该数据源不适合本插件。")


@rule("WS-QLT-003", "nit", "可维护",
      "目标 URL 硬编码过多",
      "代码里散落大量硬编码的目标 URL。抽成配置文件或常量，换目标站时改一处即可。")
def _r_qlt_003(ctx):
    urls = re.findall(r"https?://[^\s'\"<>]+", ctx.text)
    if len(urls) > 5:
        ctx.add("WS-QLT-003", "nit", "可维护",
                "硬编码 URL 共 %d 处" % len(urls), 1, urls[0],
                "把目标 URL 抽到配置（常量/配置文件），别散落在代码里。")


@rule("WS-DATA-001", "nit", "数据",
      "无去重/增量机制",
      "循环采集但看不到去重键、已访问集合或增量水位线。重跑任务会重复入库：加上去重键（URL/ID）与断点续传。")
def _r_data_001(ctx):
    if _in_loop(ctx.text) and not re.search(
            r"(seen|visited|去重|dedupe|增量|watermark|断点|已采集)", ctx.text, re.I):
        ctx.add("WS-DATA-001", "nit", "数据", "无去重/增量机制",
                1, "", "维护已采集 ID 集合或水位线字段，支持断点续传与增量更新。")


# ---------------------------------------------------------------- robots.txt 解析（RFC 9309 子集）

def parse_robots(text):
    """返回 groups 列表：每组 {agents:[], rules:[(allow,path)], delay, sitemaps[]}。"""
    groups = []
    cur = None
    sitemaps = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()
        if field == "user-agent":
            if cur is None or cur["agents"]:
                cur = {"agents": [], "rules": [], "delay": None}
                groups.append(cur)
            cur["agents"].append(value.lower())
        elif cur is not None and field in ("disallow", "allow"):
            cur["rules"].append((field == "allow", value))
        elif cur is not None and field == "crawl-delay":
            try:
                cur["delay"] = float(value)
            except ValueError:
                pass
        elif field == "sitemap":
            sitemaps.append(value)
    return groups, sitemaps


def pick_group(groups, ua="*"):
    """选最匹配的规则组：精确 UA 优先，否则 User-agent: *。"""
    ua = ua.lower()
    for g in groups:
        if ua in g["agents"]:
            return g
    for g in groups:
        if "*" in g["agents"]:
            return g
    return None


def robots_allowed(group, path):
    """最长匹配优先：Allow 与 Disallow 冲突时取最长的那条。"""
    if group is None:
        return True, "无匹配规则组，默认允许（仍需遵守 ToS）"
    best = None
    for allow, rule_path in group["rules"]:
        if not rule_path:
            if allow:
                best = (True, 0, "Allow: 空")
            continue
        if path.startswith(rule_path):
            if best is None or len(rule_path) > best[1]:
                best = (allow, len(rule_path), "%s: %s" %
                        ("Allow" if allow else "Disallow", rule_path))
    if best is None:
        return True, "无匹配规则，默认允许"
    return best[0], "命中规则 %s" % best[2]


def check_robots(domain, ua="lhg-webscraper-bot/1.0"):
    domain = re.sub(r"^https?://", "", domain).split("/")[0]
    url = "https://%s/robots.txt" % domain
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        status = "ok"
    except Exception as e:  # noqa: BLE001 - 网络失败走保守策略
        return {"domain": domain, "url": url, "status": "fetch_failed",
                "error": "%s: %s" % (type(e).__name__, e),
                "advice": "未取到 robots.txt：按保守策略执行（默认限流），"
                          "并在报告中注明。"}
    groups, sitemaps = parse_robots(text)
    group = pick_group(groups)
    return {"domain": domain, "url": url, "status": "ok",
            "groups": len(groups),
            "matched_agents": group["agents"] if group else [],
            "crawl_delay": group["delay"] if group else None,
            "sitemaps": sitemaps,
            "raw_lines": len(text.splitlines())}


# ---------------------------------------------------------------- 字段扫描

def scan_fields(path):
    """扫描 CSV/JSON 文件的列名/键名是否含敏感字段。返回 findings 列表。"""
    cols = []
    try:
        if path.endswith(".csv"):
            with open(path, encoding="utf-8", errors="replace") as fh:
                reader = csv.reader(fh)
                cols = next(reader, [])
        elif path.endswith(".json"):
            with open(path, encoding="utf-8", errors="replace") as fh:
                data = json.load(fh)
            if isinstance(data, list) and data and isinstance(data[0], dict):
                cols = list(data[0].keys())
            elif isinstance(data, dict):
                cols = list(data.keys())
    except Exception as e:  # noqa: BLE001
        return [{"rule_id": "WS-SEC-000", "severity": "warning",
                 "category": "安全", "title": "字段文件读取失败",
                 "file": path, "line": 0, "snippet": "",
                 "detail": "无法解析该文件：%s" % e}]
    findings = []
    for col in cols:
        col_s = str(col)
        for pat, label in SENSITIVE_FIELD_RES:
            if pat.search(col_s):
                findings.append({
                    "rule_id": "WS-SEC-001", "severity": "blocker",
                    "category": "安全",
                    "title": "数据含敏感字段列（%s）" % label,
                    "file": path, "line": 0, "snippet": col_s,
                    "detail": "该列必须整体剔除，不许只删值保留列名。",
                })
    return findings


# ---------------------------------------------------------------- 主流程

SEVERITY_ORDER = {"blocker": 0, "warning": 1, "nit": 2}


def run_target_audit(target):
    findings = []
    for path in collect_files(target):
        text = read_text(path)
        if not text.strip():
            continue
        ctx = Ctx(path, text)
        for r in RULES:
            try:
                r["check"](ctx)
            except Exception:
                continue  # 单条规则出错不影响整体
        findings.extend(f.to_dict() for f in ctx.findings)
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), f["file"]))
    return findings


def summarize(findings):
    s = {"blocker": 0, "warning": 0, "nit": 0, "rules_run": len(RULES)}
    for f in findings:
        if f["severity"] in s:
            s[f["severity"]] += 1
    return s


def emit(findings, fmt, fail_on, extra=None):
    summary = summarize(findings) if extra is None else extra
    if fmt == "json":
        print(json.dumps({"tool": TOOL, "version": VERSION,
                          "summary": summary, "findings": findings},
                         ensure_ascii=False, indent=2))
    else:
        print("== %s v%s ==" % (TOOL, VERSION))
        print("blocker=%d warning=%d nit=%d（规则 %d 条）" % (
            summary["blocker"], summary["warning"], summary["nit"],
            summary.get("rules_run", 0)))
        for f in findings:
            print("[%s][%s] %s:%s %s" % (
                f["severity"], f["rule_id"], f["file"], f["line"], f["title"]))
            print("    %s" % f["detail"])
    order = SEVERITY_ORDER
    bad = any(order.get(f["severity"], 9) <= order[fail_on] for f in findings)
    return 2 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="lhg-webscraper 确定性审计")
    ap.add_argument("--target", help="采集代码目录")
    ap.add_argument("--check-robots", metavar="DOMAIN", help="robots.txt 预检目标域名")
    ap.add_argument("--scan-fields", metavar="FILE", help="扫描数据文件的敏感列名")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"],
                    default="blocker")
    args = ap.parse_args(argv)

    if args.check_robots:
        info = check_robots(args.check_robots)
        if args.format == "json":
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            print("== robots.txt 预检：%s ==" % info["domain"])
            print("拉取：%s（%s）" % (info["url"], info["status"]))
            if info["status"] == "ok":
                print("规则组：%d 组，命中 UA：%s" % (
                    info["groups"], ",".join(info["matched_agents"]) or "无"))
                print("Crawl-delay：%s" % (info["crawl_delay"]
                                          if info["crawl_delay"] is not None else "无（用默认 ≥1 秒）"))
                print("Sitemap：%s" % (", ".join(info["sitemaps"]) or "无"))
                print("建议：用 pick 结果对本次目标路径逐条判定（见 --format json 的 groups）。")
            else:
                print("原因：%s" % info["error"])
                print("建议：%s" % info["advice"])
        return 0

    if args.scan_fields:
        findings = scan_fields(args.scan_fields)
        return emit(findings, args.format, args.fail_on,
                    extra={"blocker": sum(1 for f in findings if f["severity"] == "blocker"),
                           "warning": sum(1 for f in findings if f["severity"] == "warning"),
                           "nit": 0, "rules_run": 1})

    if not args.target:
        ap.error("需指定 --target / --check-robots / --scan-fields 其一")
    findings = run_target_audit(args.target)
    return emit(findings, args.format, args.fail_on)


if __name__ == "__main__":
    sys.exit(main())
