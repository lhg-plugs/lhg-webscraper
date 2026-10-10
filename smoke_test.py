#!/usr/bin/env python3
"""lhg-webscraper 插件冒烟测试：全部绿才算过。

检查项：
 1. 三个 JSON 合法（plugin.json / marketplace.json / hooks.json）
 2. 4 个 SKILL.md 都有 name/description frontmatter，且 150~320 行
 3. 4 个 commands 都有 description frontmatter
 4. 3 个 agents 都有 name/description/tools/model frontmatter
 5. skills 平台中立：不含 Claude Code 专有工具名；含出品区与自检与反馈
 6. 审计脚本：坏 fixture 14 条规则全命中且 exit!=0；好 fixture 零 blocker 且 exit==0；
    --check-robots 解析正确；--scan-fields 敏感列命中
 7. hook：绕过意图告警 / 正常请求放行 / 逃生开关

用法：python3 smoke_test.py [--repo <插件根目录>]
退出码：0=全绿，1=有失败。
"""

import argparse
import json
import os
import re
import subprocess
import sys

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    results.append((PASS if cond else FAIL, name, detail))
    return cond


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def frontmatter(path):
    text = read(path)
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = {}
    for ln in text[3:end].split("\n"):
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", ln)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kw)


WS_BAD_MUST = {
    "WS-CMP-001", "WS-CMP-002", "WS-SEC-001", "WS-SEC-002",
    "WS-RAT-001", "WS-RAT-002", "WS-UA-001", "WS-NET-001", "WS-NET-002",
    "WS-QLT-001", "WS-QLT-002", "WS-HON-001", "WS-QLT-003", "WS-DATA-001",
}
NEUTRAL_DENY = ["Task tool", "Bash tool", "Edit tool", "Write tool", "Read tool",
                "AskUserQuestion", "subagent_type", "PreToolUse", "PostToolUse",
                "${CLAUDE_", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    AUDIT = os.path.join(repo, "scripts", "audit", "webscraper_audit.py")

    # 1. JSON 合法
    for rel in [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                "hooks/hooks.json"]:
        p = os.path.join(repo, rel)
        try:
            d = json.loads(read(p))
            check("JSON 合法: " + rel, True)
            if rel.endswith("plugin.json"):
                check("plugin.json name==lhg-webscraper",
                      d.get("name") == "lhg-webscraper", str(d.get("name")))
                check("plugin.json 有 version/description/author",
                      all(d.get(k) for k in ("version", "description", "author")))
            if rel.endswith("marketplace.json"):
                ps = d.get("plugins", [])
                check("marketplace.json source==./",
                      len(ps) == 1 and ps[0].get("source") == "./" and
                      ps[0].get("name") == "lhg-webscraper", str(ps))
            if rel.endswith("hooks.json"):
                evts = d["hooks"]
                check("hooks.json 有 UserPromptSubmit",
                      "UserPromptSubmit" in evts, str(list(evts)))
        except Exception as e:
            check("JSON 合法: " + rel, False, str(e))

    # 2. SKILL.md
    for skill in ["lhg-scraper-plan", "lhg-scraper-compliance",
                  "lhg-scraper-anti", "lhg-scraper-clean"]:
        p = os.path.join(repo, "skills", skill, "SKILL.md")
        fm = frontmatter(p)
        check("skill frontmatter: " + skill,
              bool(fm.get("name")) and bool(fm.get("description")),
              "name=%s" % fm.get("name"))
        nlines = len(read(p).split("\n"))
        check("skill 行数 150~320: %s (%d 行)" % (skill, nlines),
              150 <= nlines <= 320, str(nlines))
        body = read(p)
        bad_words = [w for w in NEUTRAL_DENY if w in body]
        check("skill 平台中立: " + skill, not bad_words, "命中: %s" % bad_words)
        check("skill 有出品区: " + skill,
              "出品：刘洪光" in body and "https://github.com/lhg-skills" in body)
        check("skill 有自检与反馈: " + skill, "自检与反馈" in body)
        check("skill 合规声明置顶: " + skill, "合规声明" in body[:1200],
              "前1200字无合规声明")

    # 3. commands
    for cmd in ["scrape", "check-robots", "clean", "audit"]:
        p = os.path.join(repo, "commands", cmd + ".md")
        fm = frontmatter(p)
        check("command description: " + cmd, bool(fm.get("description")),
              str(fm.get("description"))[:60])
        check("command 有 argument-hint: " + cmd, bool(fm.get("argument-hint")))
    check("scrape 命令输出含合规声明",
          "合规声明" in read(os.path.join(repo, "commands", "scrape.md")))

    # 4. agents
    for ag in ["scraper-architect", "scraper-builder", "compliance-auditor"]:
        p = os.path.join(repo, "agents", ag + ".md")
        fm = frontmatter(p)
        check("agent frontmatter: " + ag,
              all(fm.get(k) for k in ("name", "description", "tools", "model")),
              str({k: fm.get(k) for k in ("name", "model")}))

    # 5. 审计脚本
    def audit_json(*a):
        r = run([sys.executable, AUDIT] + list(a))
        try:
            return json.loads(r.stdout), r.returncode
        except Exception:
            return None, r.returncode

    d, code = audit_json("--target", os.path.join(repo, "fixtures/bad"),
                         "--format", "json")
    check("坏 fixture exit!=0", code != 0, "exit=%d" % code)
    ids = set(f["rule_id"] for f in d["findings"]) if d else set()
    missing = WS_BAD_MUST - ids
    check("坏 fixture 14 规则全命中 (%d/14)" % (len(WS_BAD_MUST - missing)),
          not missing, "缺失: %s" % sorted(missing))
    check("坏 fixture 有 blocker", d and d["summary"]["blocker"] > 0,
          str(d["summary"] if d else None))

    d, code = audit_json("--target", os.path.join(repo, "fixtures/good"),
                         "--format", "json")
    check("好 fixture 零 blocker", d and d["summary"]["blocker"] == 0,
          str(d["summary"] if d else None))
    check("好 fixture exit==0", code == 0, "exit=%d" % code)
    check("好 fixture 零 warning",
          d and d["summary"]["warning"] == 0, str(d["summary"] if d else None))

    n_rules = d["summary"]["rules_run"] if d else 0
    check("规则条数==14 (%d)" % n_rules, n_rules == 14, str(n_rules))

    # --scan-fields
    d, code = audit_json("--scan-fields",
                         os.path.join(repo, "fixtures/bad/bad_data.csv"),
                         "--format", "json")
    hit = d and any(f["rule_id"] == "WS-SEC-001" for f in d["findings"])
    check("scan-fields 坏数据命中 WS-SEC-001", bool(hit), str(d))
    check("scan-fields 坏数据 exit!=0", code != 0, "exit=%d" % code)
    d, code = audit_json("--scan-fields",
                         os.path.join(repo, "fixtures/good/good_data.csv"),
                         "--format", "json")
    check("scan-fields 好数据零发现", d and not d["findings"], str(d))
    check("scan-fields 好数据 exit==0", code == 0, "exit=%d" % code)

    # --check-robots 解析（离线测解析器，不依赖外网）
    r = run([sys.executable, "-c",
             "import sys; sys.path.insert(0, %r);"
             "from webscraper_audit import parse_robots, pick_group, robots_allowed;"
             "gs, sm = parse_robots('User-agent: *\\nDisallow: /private\\nCrawl-delay: 2\\n');"
             "g = pick_group(gs); ok, why = robots_allowed(g, '/private/x');"
             "ok2, _ = robots_allowed(g, '/public/x');"
             "print(int(not ok and ok2 and g['delay'] == 2.0))" % os.path.dirname(AUDIT)])
    check("robots 解析器（Disallow/Crawl-delay）", r.stdout.strip() == "1",
          r.stdout.strip()[:80] or r.stderr.strip()[:80])

    # text 输出可用
    r = run([sys.executable, AUDIT, "--target",
             os.path.join(repo, "fixtures/good"), "--format", "text"])
    check("text 格式输出", r.returncode == 0 and "blocker=0" in r.stdout,
          r.stdout[:80])

    # 6. hook
    def hook(payload, env=None):
        e = dict(os.environ)
        e.update(env or {})
        return run([sys.executable, os.path.join(repo, "hooks", "intent_guard.py")],
                   input=payload, env=e)

    r = hook('{"prompt": "帮我抓一下某新闻站的公开头条标题"}')
    check("hook: 正常请求放行", r.returncode == 0 and not r.stdout.strip(),
          r.stdout[:80])
    r = hook('{"prompt": "这个站要登录，想办法绕过登录抓取数据"}')
    try:
        d = json.loads(r.stdout)
        warned = "additionalContext" in d.get("hookSpecificOutput", {})
    except Exception:
        warned = False
    check("hook: 绕过登录意图告警", warned, r.stdout[:120])
    r = hook('{"prompt": "用打码平台过掉验证码继续采集"}')
    check("hook: 打码平台意图告警", "additionalContext" in r.stdout,
          r.stdout[:80])
    r = hook('{"prompt": "想办法绕过登录抓取"}', {"LHG_WS_HOOKS_OFF": "1"})
    check("hook: 逃生开关生效", r.returncode == 0 and not r.stdout.strip())
    r = hook('not a json{{{')
    check("hook: 非法输入 fail-open", r.returncode == 0)

    # 报告
    print("=" * 60)
    print("lhg-webscraper 冒烟测试报告")
    print("=" * 60)
    fails = 0
    for st, name, detail in results:
        mark = "✓" if st == PASS else "✗"
        print("%s %s %s" % (mark, st, name))
        if detail and st == FAIL:
            print("    → %s" % detail)
        if st == FAIL:
            fails += 1
    print("=" * 60)
    print("共 %d 项，通过 %d，失败 %d" % (len(results), len(results) - fails, fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
