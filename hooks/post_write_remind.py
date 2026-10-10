#!/usr/bin/env python3
"""lhg-api-integration 硬门②（警告级，不拦截）：写 API 客户端代码时，
检测到 requests/httpx 调用却没写 timeout，或出现疑似硬编码密钥时提醒。

触发：PostToolUse / Write|Edit。只做提醒，永远 exit 0、不拦截写入。

逃生方式：LHG_API_HOOKS_OFF=1（环境变量）可关闭本提醒；
或 /plugin disable lhg-api-integration 停用整个插件。
零第三方依赖。
"""

import json
import os
import re
import sys

CODE_EXTS = {".py", ".js", ".ts"}
CALL_RE = re.compile(r"\b(requests|httpx)\s*\.\s*(get|post|put|patch|delete|request)\s*\(")
TIMEOUT_RE = re.compile(r"\btimeout\s*=")
SECRET_RE = re.compile(
    r"\b(api_key|apikey|secret|client_secret|api_token)\b\s*[:=]\s*[\"']([^\"']{8,})[\"']",
    re.I,
)
SK_RE = re.compile(r"sk-[A-Za-z0-9]{16,}")
PLACEHOLDER_RE = re.compile(r"xxx|your-|changeme|example|test|demo|placeholder", re.I)
SKIP_DIR_PARTS = {"node_modules", "dist", "build", ".git", "__pycache__", "fixtures"}


def main() -> int:
    if os.environ.get("LHG_API_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""
    if not file_path:
        return 0

    _, ext = os.path.splitext(file_path)
    if ext not in CODE_EXTS:
        return 0
    parts = file_path.replace("\\", "/").split("/")
    if any(p in SKIP_DIR_PARTS for p in parts):
        return 0
    if not os.path.isfile(file_path):
        return 0

    try:
        with open(file_path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return 0

    notes = []
    if CALL_RE.search(text) and not TIMEOUT_RE.search(text):
        notes.append("检测到 requests/httpx 调用但没写 timeout：每个请求都该带超时，"
                     "否则一个 hang 住的请求会拖死整个进程（审计规则 API-RTY-001）。")
    for m in SECRET_RE.finditer(text):
        if not PLACEHOLDER_RE.search(m.group(2)) and "environ" not in text[max(0, m.start()-40):m.start()]:
            notes.append("疑似硬编码密钥（%s=...）：请走环境变量，不要写进代码（审计规则 API-SEC-001）。"
                         % m.group(1))
            break
    if SK_RE.search(text):
        notes.append("检测到形如 sk-... 的密钥字面量：请走环境变量，不要写进代码。")

    if not notes:
        return 0

    msg = ("API 对接提醒（lhg-api-integration）：%s\n%s\n"
           "关闭本提醒：export LHG_API_HOOKS_OFF=1（当前会话有效）。"
           ) % (file_path, "\n".join("- " + n for n in notes))
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
