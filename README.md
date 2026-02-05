# Get-Biji-Knowledge

一个强大的 Claude Code 技能，让你在开发工作流中无缝搜索和检索 [Get笔记 (biji.com)](https://biji.com) 知识库内容。

## 💎 核心优势

### 为什么选择 Claude Code + 这个 Skill，而不是 Get笔记平台内的 AI？

| 维度 | Get笔记平台 AI | Claude Code + 本Skill |
|------|---------------|----------------------|
| **生态开放性** | ❌ 内容封闭在 Get笔记平台内，无法与开发工作流整合 | ✅ 知识直接注入 Claude 对话，可立即用于写代码、技术决策、文档生成等 |
| **工作流连续性** | ❌ 需要在浏览器和 IDE 之间来回切换 | ✅ 在 IDE 内一站式完成：搜索知识 → 写代码 → 提交代码 |
| **AI 能力** | ⚠️ 受平台大模型限制，模型选择和更新受制于平台 | ✅ 使用 Claude Sonnet 4.5 顶级推理能力，持续升级 |
| **多轮协作** | ⚠️ AI 回答后需手动复制粘贴到开发环境 | ✅ 知识、代码、调试在同一对话中无缝流转 |
| **跨库整合** | ✅ 支持多库查询，但结果仍在平台内 | ✅ 支持多库查询，结果可直接用于代码生成和架构设计 |
| **自动化能力** | ❌ 无法与本地开发工具联动 | ✅ 可结合 Git、测试、部署等完整开发流程 |

**核心价值**：将你的个人知识库转化为 Claude 的"专属领域知识"，让 AI 助手在编码、架构设计、技术选型时能够基于**你的**知识积累做决策，而不是通用互联网知识。

**典型场景**：
- 📖 **边查边写**："搜索我的微服务架构笔记" → Claude 基于你的笔记生成项目代码
- 🔍 **技术调研**："对比我笔记中的三种缓存方案" → Claude 整合你的知识给出决策建议
- 🛠️ **问题排查**："查我的 K8s 排障笔记" → Claude 结合笔记和当前错误日志给出解决方案
- 📝 **文档生成**："基于我的 API 设计笔记生成接口文档" → Claude 用你的规范写文档

---

## ✨ 核心功能

### 主要能力
- **🔍 智能搜索**：自然语言查询，自动重试机制应对频率限制
- **📚 多库支持**：同时搜索单个、多个或全部知识库
- **🎯 智能路由**：AI 自动匹配最相关的知识库（语义路由）
- **💡 多轮查询**：自动生成 3 种查询视角，确保结果全面
- **🔗 上下文感知**：自动维护对话历史，支持自然追问
- **📝 丰富引用**：显示来源文章标题和核心内容摘要
- **💾 文件导出**：自动保存问答和引用到 Markdown 文件
- **🧠 深度思考**：可选的高级推理模式处理复杂问题
- **⚙️ 自动描述**：使用关键词提取自动生成知识库描述

### 四种检索模式

| 模式 | 参数 | 说明 | 使用场景 |
|------|------|------|----------|
| **默认模式** | `--default` | 仅搜索默认知识库 | 日常快速查询 |
| **精准模式** | `--kb <名称>` | 指定特定知识库 | 明确领域的专项搜索 |
| **广播模式** | `--auto` | AI 自动路由到相关库 | 不确定信息在哪个库 |
| **广域模式** | `--all` | 搜索所有已配置的库 | 跨领域全面发现 |

---

## 📦 安装

1. 将此仓库克隆到 Claude Code 技能目录：
```bash
cd ~/.claude/skills/
git clone <repository-url> get-biji-knowledge
```

2. 下次启动 Claude Code 时会自动检测此技能。

---

## 🚀 快速开始

### 初次配置

首次使用需要添加 Get笔记 API 凭证：

```bash
# 添加第一个知识库
python3 scripts/biji.py config add

# 按提示输入：
# - 知识库名称（自定义标识）
# - API Key（从 https://biji.com/openapi 获取）
# - Topic ID（目标知识库的 ID）
```

**获取凭证的位置**：
1. 访问 [biji.com/openapi](https://biji.com/openapi)
2. 点击"生成API密钥"
3. 在知识库设置中找到 Topic ID

### 基础使用

在 Claude Code 对话中直接调用技能：

```
/get-biji-knowledge Docker 容器隔离的原理是什么？
```

或使用自然语言：
```
搜索我的笔记：如何优化 React 性能？
```

---

## 🎯 进阶用法

### 1. 多库联合查询

跨多个知识库同时搜索：

```bash
# 搜索指定的多个库
python3 scripts/biji.py search "微服务架构设计" --kb 后端开发 --kb DevOps

# 搜索所有库
python3 scripts/biji.py search "身份认证最佳实践" --all

# 让 AI 自动路由
python3 scripts/biji.py search "数据库索引优化策略" --auto
```

### 2. 知识库描述管理

通过添加描述提升语义路由准确度：

```bash
# 手动添加描述
python3 scripts/biji.py config update-desc 后端开发 "包含后端开发、API设计、数据库优化、微服务架构相关知识"

# 使用 AI 自动生成描述
python3 scripts/biji.py config update-desc 后端开发 --auto

# 批量更新所有描述
python3 scripts/sync_metadata.py
```

**描述撰写指南**：
- 控制在 150 字以内
- 聚焦领域、主题和关键技术
- 使用客观、中性的语言
- 避免主观评价或时效性内容

### 3. 上下文感知的追问

技能自动维护对话上下文：

```
用户："介绍一下 Redis 缓存策略"
[搜索默认知识库]

用户："缓存失效怎么处理？"
[自动在同一知识库继续搜索]

用户："现在搜索我的后端笔记"
[切换到后端知识库]
```

### 4. 范围继承

查询范围在追问中自动保持：

```bash
# 使用 --all 设置范围
python3 scripts/biji.py search "CI/CD 流水线配置" --all

# 追问自动继承 --all 范围
"Jenkins 具体怎么配置？"

# 显式指定参数可覆盖
"专门查 DevOps 笔记" --kb devops
```

### 5. 引用控制

切换引用显示：

```bash
# 关闭引用获得更简洁的输出
python3 scripts/biji.py search "什么是 REST API" --no-refs

# 重新启用引用
python3 scripts/biji.py config refs true
```

### 6. 深度思考模式

为复杂查询启用高级推理：

```bash
# 启用深度思考
python3 scripts/biji.py search "对比单体架构和微服务的权衡" --think

# 关闭以加快简单查询
python3 scripts/biji.py config think false
```

---

## ⚙️ 配置管理

### 列出所有知识库
```bash
python3 scripts/biji.py config list
```

### 设置默认知识库
```bash
python3 scripts/biji.py config set-default 后端开发
```

### 删除知识库
```bash
python3 scripts/biji.py config remove 旧笔记
```

### 会话管理
```bash
# 清除对话历史
python3 scripts/biji.py session clear

# 查看会话状态
python3 scripts/biji.py session status
```

---

## 📁 文件结构

```
get-biji-knowledge/
├── SKILL.md                 # Claude Code 技能定义
├── README.md                # 本文件
├── 使用指南.md              # 详细中文使用指南
├── scripts/
│   ├── biji.py             # 主程序入口
│   ├── search_knowledge.py # 核心搜索逻辑（含重试机制）
│   ├── config_manager.py   # 配置管理
│   ├── session_manager.py  # 上下文和会话处理
│   ├── sync_metadata.py    # 批量描述生成器
│   └── multi_search.py     # 多库协调
└── references/
    └── api_docs.md         # Get笔记 OpenAPI 文档
```

---

## 🔄 自动重试机制

技能智能处理 API 频率限制：

- **检测**：自动识别 `msg_type: 201`（超过频率限制）
- **策略**：指数退避重试 3 次（延迟 2秒、4秒、8秒）
- **透明**：向用户显示重试进度
- **降级**：所有重试失败后提供清晰的错误信息

---

## 💾 导出格式

搜索结果自动保存到：

```
/tmp/biji_knowledge/
├── search_YYYYMMDD_HHMMSS.md          # 问答内容
└── search_YYYYMMDD_HHMMSS_refs.md     # 引用来源
```

**问答文件格式**：
```markdown
# 搜索：[你的问题]

[AI 生成的答案，含内联引用]
```

**引用文件格式**：
```markdown
# 引用来源

[来源: {知识库} | 标题: {文章标题} | 核心: {内容摘要}]
...
```

---

## 🔍 多轮查询策略

为确保结果全面，每次搜索自动执行：

1. **原始查询**：你的原始问题
2. **语义变体**：使用同义词重新表述
3. **关键词提取**：核心术语和概念

结果自动整合并去重。

---

## 🔒 安全说明

- API 密钥存储在 `~/.claude/get-biji-knowledge/config.json`
- 凭证永远不会提交到版本控制（`.gitignore` 保护）
- 会话数据本地存储在 `~/.claude/get-biji-knowledge/sessions/`

---

## 💡 使用建议

1. **添加描述**：为知识库添加描述以启用 `--auto` 智能路由
2. **设置默认库**：将最常用的知识库设为默认，加快查询速度
3. **利用范围继承**：从广域范围（`--all`）开始，然后用追问精细化
4. **保持引用开启**：启用引用以验证信息来源
5. **定期更新描述**：每月运行 `sync_metadata.py` 刷新自动生成的描述

---

## 🎬 常见使用场景

### 场景 1：日常快速查询
```
# 使用默认知识库
"git rebase 交互模式的命令是什么？"
```

### 场景 2：跨领域研究
```
# 搜索所有库获得全面视角
"解释 OAuth 2.0 授权流程" --all
```

### 场景 3：领域深度钻研
```
# 针对特定领域结合上下文
"Kubernetes 网络模型详解" --kb devops --think
```

### 场景 4：探索式搜索
```
# 让 AI 找到正确的知识库
"如何实现 API 限流？" --auto
```

---

## 🔧 故障排查

### 频率限制 (msg_type: 201)
- **问题**：超过 API 频率限制（QPS: 2）
- **解决**：内置自动重试和指数退避机制

### 未找到结果
- **检查**：知识库名称是否正确？（`python3 scripts/biji.py config list`）
- **尝试**：使用 `--all` 搜索所有库
- **验证**：API Key 是否有权访问指定的 Topic ID

### 描述不生效
- **更新**：运行 `python3 scripts/biji.py config update-desc <名称> --auto`
- **验证**：确认描述在 150 字以内
- **刷新**：描述在会话期间会缓存

---

## 📚 文档

- **[SKILL.md](SKILL.md)**：技能定义和 API 参考
- **[使用指南.md](使用指南.md)**：包含示例的详细中文指南
- **[API 文档](references/api_docs.md)**：Get笔记 OpenAPI 规格说明

---

## 📋 系统要求

- Python 3.7+
- Claude Code CLI
- 拥有 API 访问权限的 Get笔记 账号
- 所需包：`requests`（自动安装）

---

## 🤝 贡献

欢迎贡献！请确保：
- 代码遵循现有模式
- 为新功能添加测试
- 相应更新文档

---

## 📄 许可证

MIT License

---

## 🔗 相关链接

- [Get笔记官网](https://biji.com)
- [Get笔记 OpenAPI](https://biji.com/openapi)
- [Claude Code 文档](https://github.com/anthropics/claude-code)

---

**💖 为 Get笔记 用户精心打造**
