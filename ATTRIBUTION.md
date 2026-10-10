# 灵感来源与致谢（Attribution）

本插件的**方法论灵感**来自以下优秀的开源项目与公开实践，**所有实现代码、检测规则与文案均为原创**，未复制任何第三方的原文案。

| 项目 | 作者 / 组织 | 许可 | 链接 | 借鉴了什么思路 |
|---|---|---|---|---|
| superpowers | Jesse Vincent（obra） | MIT | https://github.com/obra/superpowers | SDLC 硬门方法论：强制流水线 + commit 前拦截的思想；本插件 hooks 硬门受其启发 |
| OWASP API Security Top 10 | OWASP | CC BY-SA 4.0 | https://owasp.org/API-Security/ | API 安全风险分类框架（失效的对象级授权、过度数据暴露、安全配置错误等）；本插件审计规则的安全分类受其启发，**规则条目全部自研** |
| lhg-fullstack | 刘洪光 / lhg-plugs | MIT | https://github.com/lhg-plugs/lhg-fullstack | 本组织插件模板：规则注册表 + JSON/text 双输出 + exit code 语义的审计脚本模式；**规则内容全部按 API 对接领域重写** |

## 声明

1. **借鉴思路，实现与文案均为原创**：以上项目的具体文案、规则原文、代码实现均未被复制。本插件的 skill 方法论文案、审计规则、命令流程均为独立撰写。
2. **许可合规**：上述项目均为 MIT / Apache-2.0 / CC BY-SA 4.0 许可，允许在保留声明的前提下进行思路借鉴与二次创作。本文件即为保留声明的一部分。
3. **商标与归属**：各项目名称与作者署名归其各自所有者所有。

## 本插件自身的许可

本插件原创部分采用 MIT 许可（见 `LICENSE` 文件），版权所有：刘洪光（https://github.com/lhg-skills）。
