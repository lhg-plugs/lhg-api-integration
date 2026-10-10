---
description: API 文档→鉴权识别→调用封装→重试限流→联调清单，对接第三方 API 一条龙。
argument-hint: ["API 文档URL或粘贴文本"] [--lang python|node]
---

# /lhg-api-integration:api-dock —— API 对接一条龙

用户输入在 `$ARGUMENTS` 中：`"<API 文档 URL 或粘贴的文档文本>" [--lang python|node]`。默认生成 Python（requests/httpx 风格）封装代码。

## 流程（加载 lhg-api-auth → lhg-api-codegen → lhg-api-retry 全程指导）

### 1. 读文档，抓四要素
1. **Base URL**：如 `https://api.example.com/v1`（记下版本号在路径里还是 header 里）。
2. **鉴权方式**（按 lhg-api-auth 第 3 节识别三板斧）：
   - 看到 `Authorization: Bearer <token>` → Bearer Token（最常见）
   - 看到 `?api_key=` / `X-API-Key` → API Key
   - 看到 `client_id` + `client_secret` + `redirect_uri` / `grant_type` → OAuth2（最复杂，先走 `/lhg-api-integration:auth` 给小白讲明白）
   - 看到 `Authorization: Basic base64(...)` → Basic Auth（用户名:密码）
3. **核心接口清单**：每个接口的方法 + 路径 + 必填参数 + 返回示例，做成表格。
4. **坑位标注**：分页参数名（page/cursor/offset）、限流说明（X-RateLimit-* 头）、错误码表。

### 2. 生成调用封装（按 lhg-api-codegen 第 4 节模板）
- 一个 `ApiClient` 类：`__init__(base_url, credentials)` 只收凭证、不在代码里写死。
- 每个接口一个方法，参数用关键字、必填校验前置。
- **铁律**：凭证一律从环境变量读；`timeout` 每个请求必带；`raise_for_status()` 或等价错误检查必带。
- 附 `.env.example` 模板（只写变量名，不写真实值）。

### 3. 重试与限流策略（按 lhg-api-retry 第 3 节）
- 默认：超时 10s 连接 / 30s 读取；重试 3 次、指数退避（1s→2s→4s）+ 随机抖动。
- 只重试「值得重试的」：网络异常、超时、429、5xx；**不重试** 4xx（参数错了重试 100 次也没用）。
- 429 触发时读 `Retry-After` 头，按它说的等。

### 4. 联调自检清单
跑一遍确定性审计：
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/api_audit.py --target <对接代码目录> --format text
```
blocker 清零后，再按 lhg-api-ship 第 4 节做真实联调（先调通鉴权、再调一个读接口、再调写接口）。

## 交付物
- `api_client.py`（或 .js）+ `.env.example` + `API_DOCK.md`（四要素表 + 坑位标注 + 联调记录）

## 硬规则
- 密钥写进代码 → 不许，直接打回。
- 请求不带 timeout → 不许，审计脚本会标 blocker。
- 文档没看完就写代码 → 先把四要素表填完。
