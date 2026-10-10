---
name: lhg-api-auth
description: API 鉴权全解：API Key / Bearer / OAuth2 / Basic 四类识别、说人话讲解、凭证存放规范与过期刷新流程。小白对接 API 前先读它。
license: MIT
compatibility: 适用于任何支持 Markdown 指令的 AI 编程助手（Claude Code、豆包、Workbuddy 等）
metadata:
  version: 1.0.0
  author: 刘洪光
---

# lhg-api-auth：API 鉴权全解

> 目标：让没对接过 API 的小白，一次搞懂「鉴权」到底在干什么、该怎么配。
> 核心纪律：**先讲明白、再写代码；凭证永远走环境变量，绝不进代码仓库。**

## 1. 何时使用

- 拿到一份 API 文档，第一步就是识别鉴权方式 → 用本 skill 第 3 节
- 小白问「这个 token/key 放哪」→ 用第 4 节说人话解释
- OAuth2 把人绕晕了 → 用第 5 节的换票三步图
- 联调时报 401/403 → 用第 6 节排查

## 2. 输入输出

- **输入**：API 文档（URL 或粘贴文本）、或一段报错信息（如 `401 Unauthorized`）
- **输出**：「鉴权卡片」（类型 / 凭证获取 / 请求头格式 / 环境变量名 / 过期策略 / 坑位）

## 3. 分步方法论

### 第一步：识别鉴权类型（三板斧）

打开文档，先搜这几个关键词，按命中顺序判定：

| 看到的关键词 | 鉴权类型 | 通俗比喻 |
|---|---|---|
| `X-API-Key` / `?api_key=` / `apikey` | API Key | 小区门禁卡：固定字符串，每次刷 |
| `Authorization: Bearer` | Bearer Token | 电影票：先领票，每次出示，会过期 |
| `client_id` + `client_secret` + `grant_type` / `redirect_uri` | OAuth2 | 酒店办入住：多步换票，最正规也最绕 |
| `Authorization: Basic` | Basic Auth | 报暗号：用户名:密码 编码后放头里 |
| `sign` / `signature` + `timestamp` | 签名鉴权 | 对暗号+看表：参数签名，防篡改 |

**注意**：一个 API 可能混用（如 API Key + 签名），都列出来，不要只认第一个。

### 第二步：找到凭证的「领取处」

- 文档里找：Getting Started / Authentication / API Keys / Dashboard
- 记下：去哪个控制台点哪几个菜单、凭证长什么样（前缀如 `sk-`、长度大概多少）
- **当场提醒用户**：凭证只显示一次，复制好存到密码管理器，不要截图发群里

### 第三步：确定凭证的「放法」

标准答案只有一种：

```
代码里：headers = {"Authorization": f"Bearer {os.environ['API_TOKEN']}"}
仓库里：.env.example（只写 API_TOKEN=，等号后面空着）
本地：  .env（真实值，加入 .gitignore，绝不提交）
```

为什么不能写代码里？三句话讲清：
1. 代码会进 git，git 会 push，push 到公开仓库等于把家门钥匙贴在小区门口。
2. 密钥轮换时，改环境变量 1 分钟，改代码重新部署半小时。
3. 不同环境（开发/测试/生产）用不同 key，代码里写死就切不了环境。

### 第四步：讲清「过期了怎么办」

| 类型 | 过期策略 | 到期动作 |
|---|---|---|
| API Key | 一般长期有效 | 泄露/离职时去控制台 revoke，换新的 |
| Bearer（静态） | 文档写明有效期 | 到期前重新申请，更新环境变量 |
| OAuth2 access_token | 短（几小时） | 用 refresh_token 自动换（见第 5 节），换失败再走完整登录 |
| 签名 | 每次请求现算 | 时间戳对不上会 401，对时用 NTP |

### 第五步：OAuth2 换票三步（小白必看图）

```
① 用户点登录 → 跳到服务商页面授权
        ↓（带着授权码 code 跳回来）
② 你的后端拿 code + client_secret 去换 access_token（+refresh_token）
        ↓
③ 之后每次 API 请求带 access_token；过期了用 refresh_token 换新的，
   refresh_token 也过期了 → 回到第①步
```

**小白最容易踩的三个坑**：
1. `client_secret` 是服务端的命，绝不能出现在前端代码/URL 里。
2. `redirect_uri` 必须跟注册时一字不差（多一个斜杠都不行）。
3. 本地联调先用服务商提供的 playground/token 工具，别一上来就写完整流程。

### 第六步：401/403 排查清单

按顺序查，查到哪步解决就停：
1. 凭证复制全了吗（前后空格是头号凶手）？
2. 请求头名字写对了吗（`Authorization` 不是 `Authoriztion`，大小写敏感处要小心）？
3. Bearer 后面有空格吗（`Bearer <token>`，不是 `Bearer<token>`）？
4. token 过期了吗（解码看看 exp，或直接重新领一个试）？
5. 权限范围够吗（403 常是 scope 不足：申请时勾选了读，调的是写接口）？
6. IP 白名单限制吗（有些 key 绑定了服务器 IP）？

### 第七步：签名鉴权速查（国内 API 常见）

很多国内 API（支付、短信、物流）用「签名」而不用 token，流程是：

```
1. 把所有请求参数按 key 排序
2. 拼成 key1=value1&key2=value2... 的字符串
3. 末尾加上你的 secret（或 secret 包起来）
4. 做一次 MD5 / HMAC-SHA256 → 得到 sign
5. 把 sign 和其它参数一起发出去；对方用同样算法验算
```

**三个必踩的坑**：
1. **空值参不参与签名**：文档说「不参与」就别拼进去，多一个 `&key=` 签名就对不上。
2. **编码问题**：中文参数先 URL 编码还是后编码，文档怎么写就怎么做，不要自作聪明。
3. **时间戳窗口**：一般要求 `timestamp` 与服务器时间差在 5 分钟内，服务器时间用 NTP 对时。

排查签名 401：把「你拼的待签名字符串」打印出来，跟文档示例逐字符对比 —— 99% 是排序/编码/空值三选一的问题。

### 第八步：凭证轮换与多人协作

- **轮换节奏**：API Key 至少每 90 天换一次；人员离职当天 revoke 他的 key。
- **多环境隔离**：开发/测试/生产三套 key，测试 key 泄露了不影响生产。
- **交接规范**：新 key 只通过密码管理器/加密渠道交接，不许截图、不许明文发邮件。
- **泄露应急**：怀疑泄露 → 1 分钟内去控制台 revoke → 换新 key → 更新环境变量 → 查调用日志看有没有异常调用。

## 4. 反模式（不要这么干）

- ❌ `API_KEY = "sk-abc123..."` 写在代码里 —— 泄露+难轮换
- ❌ 把 `.env` 提交到 git —— 等于公开密钥
- ❌ 前端 JS 里放 client_secret —— 用户打开控制台全看得到
- ❌ 401 了就无脑重试 —— 先查凭证，重试解决不了配错的问题
- ❌ 一个 key 多人共用还不记在哪 —— 泄露了都不知道 revoke 哪个
- ❌ 把密钥截图发到群里/issue 里 —— 发完立刻去控制台 revoke 重发

## 5. 自检与反馈

每次用完本 skill，做一次轻量自检：

1. 鉴权卡片六项（类型/领取处/请求头/环境变量/过期策略/坑位）填全了吗？
2. 代码里搜一遍真值残留（`sk-` / `Bearer ey` / 长随机字符串），确认没有？
3. `.env` 在不在 `.gitignore` 里？`.env.example` 有没有同步更新？
4. OAuth2 的话：换票三步给用户讲过一遍了吗？

标准冒烟用例：拿一份公开 API 文档（如 OpenWeatherMap / GitHub API），按第 3 节输出鉴权卡片，检查类型判定与请求头格式是否正确。

反馈渠道：以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-api-integration/issues，正文写清「输入 → 错误输出 → 期望输出」。

## 出品：刘洪光

本 skill 由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
