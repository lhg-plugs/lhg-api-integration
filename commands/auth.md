---
description: 鉴权小课堂：用说人话的方式讲清 API Key / Bearer / OAuth2 / Basic 该用哪个、怎么配。
argument-hint: ["要对接的 API 名称或文档片段"]
---

# /lhg-api-integration:auth —— 鉴权小课堂

用户输入在 `$ARGUMENTS` 中：要对接的 API 名称或文档片段。**这个命令不写代码，只负责把鉴权讲明白**——小白先懂、再动手。

## 流程（加载 lhg-api-auth 全程指导）

### 1. 一句话定位
先问用户（或从文档判断）：这个 API 的鉴权属于哪一类？
- **API Key**：像「小区门禁卡」——一串固定字符串，每次请求带上就行。例子：`X-API-Key: abc123` 或 URL 里 `?api_key=abc123`。
- **Bearer Token**：像「电影票」——先拿票（登录/申请），之后每次请求出示：`Authorization: Bearer <票>`。票会过期，过期了重拿。
- **OAuth2**：像「酒店前台办入住」——流程最长：拿着 client_id/client_secret 去换授权码、再换 access_token，还要管刷新（refresh_token）。用户登录类场景几乎都是它。
- **Basic Auth**：像「报暗号」——用户名:密码 base64 一下放 header 里。简单但裸奔，必须配 HTTPS。

### 2. 说人话讲清三件事（按 lhg-api-auth 第 4 节）
1. **凭证长什么样**：给用户看真实格式示例（用占位符，不用真值）。
2. **凭证放哪**：环境变量；`.env.example` 长什么样；**为什么不能写代码里**（git 一 push 全世界可见）。
3. **过期了怎么办**：API Key 一般不过期（丢了就 revoke 重发）；Bearer/Access Token 过期 → 刷新流程画出来。

### 3. 输出「鉴权卡片」
```markdown
## 鉴权卡片：<API 名称>
- 类型：Bearer Token
- 凭证获取：<去哪里申请>
- 请求头：`Authorization: Bearer ${API_TOKEN}`
- 环境变量：`API_TOKEN`
- 过期策略：<多久过期 / 如何刷新>
- 坑：<文档里藏着的注意事项>
```

## 硬规则
- 不许跳过讲解直接甩代码 —— 小白配错鉴权，联调 90% 的时间都浪费在这。
- 讲 OAuth2 时必须画出「换票三步」，不许只说「去看文档」。
