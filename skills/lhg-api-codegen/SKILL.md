---
name: lhg-api-codegen
description: API 调用封装代码生成：从文档四要素到 ApiClient 类模板，含凭证管理、超时、错误检查、分页封装的落地规范。
license: MIT
compatibility: 适用于任何支持 Markdown 指令的 AI 编程助手（Claude Code、豆包、Workbuddy 等）
metadata:
  version: 1.0.0
  author: 刘洪光
---

# lhg-api-codegen：API 调用封装代码生成

> 目标：把 API 文档变成一份「别人能直接用、不敢乱用」的客户端代码。
> 核心纪律：**封装一次，到处复用；脏活（鉴权/超时/报错）收敛在客户端内部，不泄漏给调用方。**

## 1. 何时使用

- 鉴权卡片已定（先过 lhg-api-auth），开始写调用代码 → 用本 skill
- 已有一堆散落的 `requests.get(...)` 想收敛成客户端类 → 用第 4 节重构
- 联调时发现每个接口都在重复写 header/timeout → 回来看第 4 节模板

## 2. 输入输出

- **输入**：鉴权卡片 + 接口清单表（方法/路径/必填参数/返回示例）+ 目标语言（Python/Node，默认 Python）
- **输出**：`api_client.py`（或 `.js`）+ `.env.example` + 接口方法清单

## 3. 分步方法论

### 第一步：先画「四要素表」（不动代码，先填表）

| 要素 | 内容 | 例 |
|---|---|---|
| Base URL | 含版本号 | `https://api.example.com/v1` |
| 鉴权头 | 固定写法 | `Authorization: Bearer {token}` |
| 分页约定 | 参数名+翻页方式 | `page`+`per_page`，或 `cursor` |
| 错误形状 | 失败时返回什么 | `{"code": 40001, "message": "..."}` |

表没填完不写代码 —— 写代码时反复翻文档是效率杀手。

### 第二步：定客户端骨架（所有语言通用）

```
ApiClient
├── __init__(base_url, credentials)   # 只收凭证，不在内部写死
├── _request(method, path, ...)       # 唯一出口：拼 header、加 timeout、统一报错
├── _paginate(...)                   # 分页循环收敛在这里
└── 接口方法                          # get_user / create_order ... 一个接口一个方法
```

**为什么要有 `_request` 唯一出口**：以后加日志、加重试、换鉴权方式，只改这一个地方。不收敛的话，20 个接口就是 20 处要改。

### 第三步：写接口方法（三条铁律）

1. **参数前置校验**：必填参数在发请求前就检查，缺了直接抛错并说清缺哪个 —— 别等 API 返回 400 才知道。
2. **返回值裁剪**：只返回调用方关心的字段，不要把原始大 JSON 原样甩出去（上游一改字段，调用方全崩）。
3. **错误翻译**：把 API 的错误码翻译成人话（如 `40001 → "参数缺失：..."`），并保留原始响应供排查。

### 第四步：Python 模板（可直接套用，按需删减）

```python
import os
import requests

class ApiClient:
    """<API 名称> 调用封装。凭证从环境变量读取。"""

    def __init__(self, base_url=None, api_token=None, timeout=30):
        self.base_url = (base_url or os.environ.get("API_BASE_URL",
                         "https://api.example.com/v1")).rstrip("/")
        self.api_token = api_token or os.environ.get("API_TOKEN")
        if not self.api_token:
            raise ValueError("缺 API_TOKEN 环境变量：复制 .env.example 为 .env 并填写")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        })

    def _request(self, method, path, **kwargs):
        """唯一出口：超时、报错收敛在这里。"""
        url = self.base_url + path
        kwargs.setdefault("timeout", self.timeout)
        resp = self.session.request(method, url, **kwargs)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise ApiError.from_response(resp) from e
        return resp.json()

    def list_items(self, page=1, per_page=20):
        """示例：列表接口（分页参数显式暴露）。"""
        return self._request("GET", "/items",
                             params={"page": page, "per_page": per_page})

    def iter_all_items(self, per_page=100):
        """示例：全量拉取（分页循环收敛，有终止条件）。"""
        page = 1
        while True:
            data = self.list_items(page=page, per_page=per_page)
            items = data.get("items", [])
            if not items:
                break
            yield from items
            if len(items) < per_page:  # 最后一页
                break
            page += 1


class ApiError(Exception):
    """API 错误：人话 message + 原始 code/response 保留排查用。"""

    def __init__(self, message, code=None, response=None):
        super().__init__(message)
        self.code = code
        self.response = response

    @classmethod
    def from_response(cls, resp):
        try:
            body = resp.json()
        except Exception:
            body = {}
        code = body.get("code", resp.status_code)
        message = body.get("message", "请求失败（HTTP %s）" % resp.status_code)
        hint = ERROR_HINTS.get(code, "")
        return cls("%s%s" % (message, ("；" + hint) if hint else ""),
                   code=code, response=resp.text[:2000])


# 错误码翻译表：从文档错误码表逐条搬运
ERROR_HINTS = {
    40001: "检查必填参数是否齐全",
    40101: "token 无效或过期，重新获取后更新环境变量",
    42901: "触发限流，降低调用频率后重试",
}
```

Node（fetch/axios）版本结构相同：`constructor` 收凭证、`_request` 唯一出口、`ApiError` 翻译表，三件套缺一不可。

### 第五步：`.env.example` 模板

```
# 复制为 .env 并填写真实值；.env 绝不提交到 git
API_BASE_URL=https://api.example.com/v1
API_TOKEN=
# OAuth2 才需要下面两行：
# API_CLIENT_ID=
# API_CLIENT_SECRET=
```

### 第六步：联调前自查（再跑一遍确定性脚本）

用插件自带的审计脚本扫一遍（`scripts/audit/api_audit.py`），blocker 清零再去调真实接口 —— 带着密钥硬编码去联调，等于裸奔上路。

## 4. 反模式（不要这么干）

- ❌ 每个接口手写 `requests.get(url, headers={...}, timeout=...)` —— 20 个接口 20 处 header，换鉴权方式时哭
- ❌ 返回原始大 JSON 给调用方 —— 上游加个字段就全崩
- ❌ 接口方法里拼 URL 字符串 —— 路径一改处处改，用 `base_url + path`
- ❌ 把分页循环写在业务代码里 —— 收敛到 `iter_all_*`，业务只管 `for item in ...`
- ❌ 错误直接 `raise Exception(resp.text)` —— 调用方看不懂，排查也困难
- ❌ 模板里的 `ERROR_HINTS` 留空上线 —— 文档有错误码表就逐条搬，这是联调效率的关键

## 5. 自检与反馈

每次用完本 skill，做一次轻量自检：

1. 所有请求都经过 `_request` 唯一出口吗？（搜一下有没有漏网的 `requests.` 直接调用）
2. 每个请求都有 timeout 吗？（审计脚本 API-RTY-001 会查）
3. 凭证有没有硬编码？（搜 `sk-` / 长字符串字面量）
4. `.env.example` 和代码里的环境变量名对得上吗？
5. 错误码翻译表覆盖了文档里的常见码吗？

标准冒烟用例：给一个 3 接口的假 API 文档生成客户端，检查：凭证走环境变量、有 timeout、有 `_request` 收敛、有分页方法。

反馈渠道：以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-api-integration/issues，正文写清「输入 → 错误输出 → 期望输出」。

## 出品：刘洪光

本 skill 由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
