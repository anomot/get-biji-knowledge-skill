# Get笔记知识库 (Get Biji Knowledge)

> Claude Code 技能：集成 Get 笔记（biji.com）知识库的 OpenAPI，让 Claude 能够搜索和访问你的个人知识库。

## ✨ 特性

- 🔍 **AI 驱动的知识搜索** - 从你的 Get 笔记知识库中智能检索信息
- 🤖 **深度思考模式** - 支持复杂问题的深入分析
- 📚 **引用追踪** - 自动记录和引用来源笔记
- 💬 **自动上下文管理** - 追问时自动保留对话历史
- 📝 **Markdown 导出** - 自动保存问答记录和引用来源
- ⚙️ **一次配置永久使用** - 安全存储 API 凭证

## 🚀 快速开始

### 1. 获取 API 凭证

1. 访问 [Get 笔记知识库](https://www.biji.com/subject)
2. 进入你的知识库
3. 点击「API 设置」
4. 复制你的 **API Key** 和 **知识库 ID**

### 2. 配置知识库（仅需一次）

```bash
python3 scripts/biji.py config add \
  --name "我的笔记" \
  --api-key "YOUR_API_KEY" \
  --topic-id "YOUR_TOPIC_ID" \
  --default
```

### 3. 开始搜索

```bash
# 简单搜索
python3 scripts/biji.py search "你的问题"

# 追问（自动保留上下文）
python3 scripts/biji.py search "更详细的内容？"

# 开始新话题
python3 scripts/biji.py search "新问题" --new
```

## 📖 文档

- **[SKILL.md](SKILL.md)** - 完整的技术文档和高级用法
- **[使用指南.md](使用指南.md)** - 用户友好的使用说明（推荐新手阅读）
- **[API 参考](references/api_reference.md)** - Get 笔记 OpenAPI 详细文档

## 💡 使用示例

### 配置多个知识库

```bash
# 添加第一个仓库（设为默认）
python3 scripts/biji.py config add --name "政经参考" --api-key KEY --topic-id ID1 --default

# 添加第二个仓库（使用同一个 API Key）
python3 scripts/biji.py config add --name "技术笔记" --api-key KEY --topic-id ID2

# 查看所有配置
python3 scripts/biji.py config list
```

### 切换知识库搜索

```bash
# 搜索默认知识库
python3 scripts/biji.py search "问题"

# 搜索指定知识库
python3 scripts/biji.py search "技术问题" --kb "技术笔记"
```

### 控制引用显示

```bash
# 开启全局引用（默认）
python3 scripts/biji.py config set refs true

# 关闭全局引用
python3 scripts/biji.py config set refs false
```

## 📂 文件结构

```
get-biji-knowledge/
├── SKILL.md              # 技能说明文档
├── 使用指南.md            # 用户使用指南
├── references/           # API 参考文档
│   └── api_reference.md
└── scripts/              # Python 脚本
    ├── biji.py          # 主程序（推荐使用）
    ├── config_manager.py # 配置管理
    ├── session_manager.py # 会话管理
    ├── search_knowledge.py # 底层搜索 API
    └── recall_knowledge.py # 召回 API
```

## 🔒 安全说明

- **API Key 安全**: 配置文件存储在 `~/.claude/skills/get-biji-knowledge/config.json`，不会被提交到 git
- **不要泄露凭证**: 永远不要在公开场合分享你的 API Key 和知识库 ID
- **.gitignore**: 已配置忽略所有用户数据和配置文件

## 📋 功能清单

- ✅ 一次配置，永久使用
- ✅ 自动管理对话上下文
- ✅ 双文件导出（问答 + 引用）
- ✅ 全局引用开关
- ✅ 多知识库支持
- ✅ 一个 API Key 可用于所有仓库
- ✅ 深度思考模式
- ✅ 会话管理
- ✅ 自动文件累积

## 🛠️ 高级用法

查看 [SKILL.md](SKILL.md) 了解：
- 底层 API 脚本使用
- 自定义集成
- 手动上下文管理
- 原始召回结果

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🔗 相关链接

- [Get 笔记官网](https://www.biji.com/)
- [Claude Code](https://github.com/anthropics/claude-code)
- [API 文档](references/api_reference.md)

---

**Made with ❤️ for Get 笔记 users**
