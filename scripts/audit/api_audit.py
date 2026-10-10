#!/usr/bin/env python3
"""lhg-api-integration 确定性对接审计：18 条规则，零第三方依赖。

扫描目标目录的 API 客户端代码（Python / JS / TS），输出 JSON 与人类可读报告；
有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。

用法：
    python3 api_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则全部原创（方法论见插件 skills/ 下的 lhg-api-auth/codegen/retry/ship，
未复制任何第三方 skill/插件的原文案与代码）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-api-integration/api-audit"

SKIP_DIRS = {
    "node_modules", ".next", "dist", "build", ".git", "coverage",
    "__pycache__", "vendor", ".turbo", "out", "fixtures",
}
SCAN_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx"}
PLACEHOLDER_RE = re.compile(r"xxx|your-|changeme|example|test|demo|placeholder|password123", re.I)
CALL_RE = re.compile(r"\b(requests|httpx|fetch|axios)\s*[\.(]\s*(get|post|put|patch|delete|request)?")


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line", "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line, snippet, detail):
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


def collect_files(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext in SCAN_EXTS:
                out.append(os.path.join(root, f))
    return sorted(out)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _hit(rule_id, path, lineno, snippet):
    rule = _RULE_BY_ID[rule_id]
    return Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                   path, lineno, snippet[:160], rule["detail"])


def _file_hit(rule_id, path):
    return _hit(rule_id, path, 1, os.path.basename(path))


RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity,
             "category": category, "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


# ---------------- 安全 ----------------

@rule("API-SEC-001", "blocker", "安全", "密钥硬编码",
      "代码里直接写密钥/token。走环境变量，仓库里只留 .env.example 模板。")
def r_sec_001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if "environ" in ln or "getenv" in ln or "process.env" in ln:
            continue
        m = re.search(
            r"\b(api_key|apikey|api_token|secret|client_secret|private_key)\b"
            r"\s*[:=]\s*[\"']([^\"']+)[\"']", ln, re.I)
        if m and len(m.group(2)) >= 6 and not PLACEHOLDER_RE.search(m.group(2)):
            out.append(_hit("API-SEC-001", path, i + 1, ln.strip()))
    for m in re.finditer(r"sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}", text):
        lineno = text[:m.start()].count("\n") + 1
        out.append(_hit("API-SEC-001", path, lineno, lines[lineno - 1].strip()))
    # Authorization 头里直接拼字面量 token
    for i, ln in enumerate(lines):
        if re.search(r"Authorization[\"']?\s*[:=]\s*[\"']Bearer [A-Za-z0-9\-_.]{16,}[\"']", ln):
            out.append(_hit("API-SEC-001", path, i + 1, ln.strip()))
    return out


@rule("API-SEC-002", "blocker", "安全", "密钥写入日志",
      "print/log 了密钥变量。日志会进文件、进监控，等于把密钥广播出去。")
def r_sec_002(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"\b(print|console\.log|logger?\.(info|debug|error))\s*\(.*\b(api_key|apikey|api_token|secret|client_secret|password)\b",
                     ln, re.I):
            out.append(_hit("API-SEC-002", path, i + 1, ln.strip()))
    return out


@rule("API-SEC-003", "warning", "安全", "明文 HTTP 接口地址",
      "base_url 用 http://，凭证裸奔。必须 https（本地联调 127.0.0.1 除外）。")
def r_sec_003(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        for m in re.finditer(r"http://[A-Za-z0-9.\-]+", ln):
            if "127.0.0.1" in m.group(0) or "localhost" in m.group(0):
                continue
            out.append(_hit("API-SEC-003", path, i + 1, ln.strip()))
            break
    return out


@rule("API-SEC-004", "warning", "安全", "密钥放在 URL 参数里",
      "api_key 拼在 URL/query 里会被代理日志、浏览器历史记录下来。改走请求头。")
def r_sec_004(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"""params\s*=\s*\{[^}]*\b(api_key|apikey|token|secret)\b""", ln, re.I):
            out.append(_hit("API-SEC-004", path, i + 1, ln.strip()))
        elif re.search(r"""\?[^"']*\b(api_key|apikey|token)=\w""", ln, re.I):
            out.append(_hit("API-SEC-004", path, i + 1, ln.strip()))
    return out


@rule("API-SEC-005", "blocker", "安全", "关闭证书校验",
      "verify=False / rejectUnauthorized=false 让中间人攻击畅通无阻。绝不允许。")
def r_sec_005(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"\bverify\s*=\s*False\b", ln) or \
           re.search(r"rejectUnauthorized\s*:\s*false", ln, re.I):
            out.append(_hit("API-SEC-005", path, i + 1, ln.strip()))
    return out


# ---------------- 健壮性：超时与重试 ----------------

@rule("API-RTY-001", "blocker", "健壮性", "请求未设置超时",
      "requests/httpx/fetch 调用没带 timeout，一个 hang 住的请求拖死整个进程。")
def r_rty_001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"\b(requests|httpx)\s*\.\s*(get|post|put|patch|delete|request)\s*\(", ln):
            # 同一行或续行找 timeout
            window = "\n".join(lines[i:i + 4])
            if not re.search(r"\btimeout\s*=", window):
                out.append(_hit("API-RTY-001", path, i + 1, ln.strip()))
        elif re.search(r"\bfetch\s*\(", ln):
            window = "\n".join(lines[i:i + 6])
            if "AbortController" not in window and "signal" not in window:
                out.append(_hit("API-RTY-001", path, i + 1, ln.strip()))
    return out


@rule("API-RTY-002", "warning", "健壮性", "缺少重试机制",
      "文件里有 API 调用，但全文件找不到 retry/tenacity/backoff 字样。网络偶发失败时只能裸崩。")
def r_rty_002(lines, text, path, ctx):
    if not CALL_RE.search(text):
        return []
    if re.search(r"retry|retries|tenacity|backoff|resilient", text, re.I):
        return []
    return [_file_hit("API-RTY-002", path)]


@rule("API-RTY-003", "warning", "健壮性", "重试无退避上限",
      "有重试但没看到退避/上限（backoff/max_attempts/max_retries）。固定间隔重试在对方雪崩时是帮倒忙。")
def r_rty_003(lines, text, path, ctx):
    if not re.search(r"retry|retries", text, re.I):
        return []
    if re.search(r"backoff|max_attempts|max_retries|exponential", text, re.I):
        return []
    return [_file_hit("API-RTY-003", path)]


@rule("API-RTY-004", "blocker", "健壮性", "无限重试循环",
      "while True 里发请求且没有 break/次数上限，失败时配额烧光、日志爆炸。")
def r_rty_004(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"^\s*while\s+True\s*:", ln):
            window = "\n".join(lines[i:i + 25])
            if CALL_RE.search(window) and not re.search(r"\bbreak\b|attempt\s*>|count\s*>|max_", window):
                out.append(_hit("API-RTY-004", path, i + 1, ln.strip()))
    return out


# ---------------- 限流 ----------------

@rule("API-LIM-001", "warning", "限流", "未处理 429 限流",
      "全文件没出现 429。对方限流时你只能裸崩，正确做法是读 Retry-After 退避等待。")
def r_lim_001(lines, text, path, ctx):
    if not CALL_RE.search(text):
        return []
    if "429" in text or "Retry-After" in text or "retry_after" in text:
        return []
    return [_file_hit("API-LIM-001", path)]


@rule("API-LIM-002", "warning", "限流", "缺客户端本地节流",
      "没看到本地节流（rate_limit/节流/请求间隔控制）。顶着配额上限跑，迟早吃 429。")
def r_lim_002(lines, text, path, ctx):
    if not CALL_RE.search(text):
        return []
    if re.search(r"rate_limit|ratelimit|throttl|_last_request|sleep\(.*\)", text, re.I):
        return []
    return [_file_hit("API-LIM-002", path)]


# ---------------- 分页 ----------------

@rule("API-PAG-001", "warning", "分页", "列表请求无分页参数",
      "有列表类请求（list/items/search），但全文件没出现 page/per_page/limit/cursor/offset。数据量一大就爆。")
def r_pag_001(lines, text, path, ctx):
    if not re.search(r"list|items|search|query", text, re.I):
        return []
    if re.search(r"\bpage\b|per_page|page_size|\blimit\b|cursor|offset", text, re.I):
        return []
    return [_file_hit("API-PAG-001", path)]


@rule("API-PAG-002", "warning", "分页", "分页循环无终止条件",
      "翻页循环里没看到 has_more/next_cursor/总数判断，可能死循环拉到天荒地老。")
def r_pag_002(lines, text, path, ctx):
    if not re.search(r"\bpage\b", text, re.I):
        return []
    if not re.search(r"while", text):
        return []
    if re.search(r"has_more|next_cursor|next_page|total_pages|len\(.*\)\s*<\s*per_page", text, re.I):
        return []
    return [_file_hit("API-PAG-002", path)]


# ---------------- 错误处理 ----------------

@rule("API-ERR-001", "blocker", "错误处理", "空异常吞没",
      "except 里只有 pass/continue，错误被静默吃掉，出问题时无从排查。")
def r_err_001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"^\s*except\b.*:\s*$", ln):
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if nxt in ("pass", "continue", "..."):
                out.append(_hit("API-ERR-001", path, i + 1, ln.strip()))
    return out


@rule("API-ERR-002", "warning", "错误处理", "错误码不分级",
      "没看到 raise_for_status 或 status_code 分支。4xx（自己的错）和 5xx（对方的错）不分，重试策略无从谈起。")
def r_err_002(lines, text, path, ctx):
    if not CALL_RE.search(text):
        return []
    if re.search(r"raise_for_status|status_code|response\.ok|\.status\b", text):
        return []
    return [_file_hit("API-ERR-002", path)]


@rule("API-ERR-003", "warning", "错误处理", "错误响应未翻译",
      "直接抛原始响应文本给调用方。应翻译成人话并保留原始 code 供排查（见 lhg-api-codegen 的 ApiError）。")
def r_err_003(lines, text, path, ctx):
    if not re.search(r"raise\s+Exception\s*\(\s*(resp|response|r)\.(text|content)", text):
        return []
    return [_file_hit("API-ERR-003", path)]


# ---------------- 可维护性 ----------------

@rule("API-DOC-001", "nit", "可维护性", "封装函数缺文档",
      "def 定义的函数没有 docstring/注释。接口方法至少一句话说明它是调哪个接口。")
def r_doc_001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"^\s*def\s+\w+\s*\(", ln) and not ln.strip().startswith("def __"):
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            nxt2 = lines[i + 2].strip() if i + 2 < len(lines) else ""
            if not (nxt.startswith('"""') or nxt.startswith("'''") or nxt.startswith("#")
                    or nxt2.startswith('"""') or nxt2.startswith("'''")):
                out.append(_hit("API-DOC-001", path, i + 1, ln.strip()))
    return out


@rule("API-CFG-001", "nit", "可维护性", "URL 字面量散落",
      "文件里出现 3 处以上 URL 字面量。收敛到 base_url + path，别处处手写完整 URL。")
def r_cfg_001(lines, text, path, ctx):
    urls = re.findall(r"https?://[A-Za-z0-9.\-_/]+", text)
    distinct = {u.split("?")[0] for u in urls}
    if len(distinct) >= 3:
        return [_file_hit("API-CFG-001", path)]
    return []


def run(target):
    files = collect_files(target)
    findings = []
    ctx = {}
    for path in files:
        text = read_text(path)
        lines = text.split("\n")
        rel = os.path.relpath(path, target)
        for r in RULES:
            try:
                findings.extend(r["check"](lines, text, rel, ctx))
            except Exception:
                pass
    return files, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="lhg-api-integration 确定性对接审计")
    ap.add_argument("--target", default=".", help="扫描目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"], default="blocker")
    args = ap.parse_args(argv)

    target = os.path.abspath(args.target)
    if not os.path.isdir(target):
        print("target 不是目录：%s" % args.target, file=sys.stderr)
        return 1

    files, findings = run(target)

    sev_rank = {"blocker": 3, "warning": 2, "nit": 1}
    counts = {"blocker": 0, "warning": 0, "nit": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    result = {
        "tool": TOOL,
        "version": VERSION,
        "target": args.target,
        "summary": {
            "files_scanned": len(files),
            "rules_run": len(RULES),
            "blocker": counts["blocker"],
            "warning": counts["warning"],
            "nit": counts["nit"],
        },
        "findings": [f.to_dict() for f in sorted(
            findings, key=lambda x: (-sev_rank.get(x.severity, 0), x.file, x.line))],
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        s = result["summary"]
        print("API 对接审计：扫描 %d 文件，运行 %d 条规则" % (s["files_scanned"], s["rules_run"]))
        print("blocker=%d warning=%d nit=%d" % (s["blocker"], s["warning"], s["nit"]))
        for f in result["findings"]:
            print("[%s][%s] %s:%d %s" % (
                f["severity"].upper(), f["rule_id"], f["file"], f["line"], f["title"]))
            print("    %s" % f["detail"])
            if f["snippet"]:
                print("    → %s" % f["snippet"])

    level = sev_rank[args.fail_on]
    bad = any(sev_rank.get(f.severity, 0) >= level for f in findings)
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
