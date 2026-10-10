<!-- About 简介（推送后填写到仓库 About 栏）：
API 对接专家：文档→鉴权→封装→重试限流→联调自检一条龙 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-api-integration
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, api, rest, integration -->

# lhg-api-integration：API 对接专家

> **一句话介绍**：给 AI 编程助手装上"API 对接一条龙"——文档→鉴权识别（说人话讲清 OAuth2）→调用封装代码生成→重试/限流/熔断策略→18 条确定性规则联调自检，小白也能稳稳对接第三方 API。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-api-integration
> /plugin install lhg-api-integration@lhg-plugs
> ```

## 它是什么

`lhg-api-integration` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **4 个命令**（小白入口）：`api-dock` 对接一条龙，`auth` 鉴权小课堂（先讲明白再动手），`check` 对接代码体检，`rateplan` 限流与重试策略设计
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：鉴权全解、调用封装代码生成、重试/超时/限流/熔断、自检与联调上线
- **2 个专家 agent**：对接构建、独立评审
- **2 个硬门 hooks**：commit 前审计拦截、无超时/硬编码密钥的代码提醒（均可一键豁免）
- **18 条确定性对接审计规则**：纯 Python、零第三方依赖，5 秒出结果

## 4 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-api-integration:api-dock` | API 文档→鉴权识别→封装代码→重试策略→联调清单，一条龙 | `/lhg-api-integration:api-dock "https://docs.example.com"` |
| `/lhg-api-integration:auth` | 鉴权小课堂：说人话讲清 API Key / Bearer / OAuth2 该用哪个 | `/lhg-api-integration:auth "Stripe"` |
| `/lhg-api-integration:check` | 对接代码体检（脚本 + 人工评审清单） | `/lhg-api-integration:check ./my-client` |
| `/lhg-api-integration:rateplan` | 按 API 限流档位定制退避、熔断与降级方案 | `/lhg-api-integration:rateplan "OpenAI" --qps 5` |

## 自查说明

自查 = 确定性脚本（机器）+ 人工评审清单（人）：

1. 先跑 `scripts/audit/api_audit.py`（18 条规则：密钥硬编码、无超时、无重试、无限重试、429 未处理、分页缺失、空异常吞没等），零 LLM 成本；
2. 发现分三级：**blocker**（必须修，commit 前 hook 会拦截）、**warning**（修或写豁免理由）、**nit**（顺手修）；
3. 再按 `lhg-api-ship` skill 的联调六步过一遍脚本抓不到的（凭证真值残留、不该重试的是否重试、分页终止条件）。

blocker 清零才算对接完；为清零改规则算作弊，不许。

## 目录结构

```
lhg-api-integration/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 4 个命令：api-dock / auth / check / rateplan
├── skills/                  # 4 个平台中立 skill（lhg-api-auth/codegen/retry/ship）
├── agents/                  # 2 个专家 agent（dock-builder / dock-reviewer）
├── hooks/                   # 2 个硬门（commit 前审计拦截 / 无超时提醒）+ 豁免说明
├── scripts/audit/           # 18 条确定性对接审计规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你要对接第三方 API（支付、短信、地图、AI 模型……），但没对接过、怕踩坑时 → 用 `/lhg-api-integration:api-dock`
- 文档里的 OAuth2 把你绕晕了 → 先跑 `/lhg-api-integration:auth`，讲明白再动手
- 已经写了一堆 `requests.get`，想收敛成规范的客户端类时 → 对接构建专家帮你重构
- 对接代码要上线，怕有密钥泄露、无超时、无重试这类硬伤时 → 跑 `/lhg-api-integration:check`
- 批量调用被限流 429 封过 key → 用 `/lhg-api-integration:rateplan` 定策略

**什么时候不用：**

- 你对接的是自家内部 API、鉴权就是内网直连 → 鉴权小课堂和密钥规则对你多余
- 你只需要调一两个接口做一次性脚本 → 全套封装是杀鸡用牛刀，直接写裸调用即可
- 你的语言不是 Python/JS（如 Go/Java）→ skill 方法论通用，但代码模板和审计脚本需要自己改

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-api-integration](https://github.com/lhg-plugs/lhg-api-integration) | API 对接专家：文档→鉴权→封装→重试限流→联调自检一条龙 | `/plugin install lhg-api-integration@lhg-plugs` |
| *（后续插件在此追加，保持表格格式一致）* | | |

## 自检与反馈

- 每次用完任一 skill，按其「自检与反馈」节做轻量自检。
- 标准冒烟用例：`python3 smoke_test.py`（仓库根目录），全绿才算过。
- 反馈渠道：以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-api-integration/issues，正文写清「输入 → 错误输出 → 期望输出」。规则误报/漏报请附最小复现代码。

## 出品

**出品：刘洪光**（安徽合肥），归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
