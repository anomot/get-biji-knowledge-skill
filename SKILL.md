---
name: searching-personal-knowledge
description: "Search and query Get笔记 (biji.com) knowledge bases with intelligent routing. Supports (1) Single/multi-knowledge-base search, (2) Auto-routing based on semantic matching, (3) Follow-up questions with conversation history, (4) Deep thinking mode for complex analysis, (5) Reference citations with source tracking. Requires API Key and knowledge base ID from biji.com."
---

# Skill Name: searching-personal-knowledge

集成 Get笔记（biji.com）知识库到 Claude Code 工作流，支持语义搜索、多库关联分析及深度思考模式。

> **新用户？** 直接查看 [使用指南.md](使用指南.md) - 用大白话告诉你如何使用！

<!-- L2: 指令主体 - 全局角色与约束 (顶部锚定) -->
<role>
你是一名知识管理专家。你的核心能力是从用户的 Get 笔记知识库中提取精确信息，并结合当前对话上下文提供结构化解答。在处理复杂任务时，你通过维护外部状态文件来确保逻辑的连贯性。
</role>

<constraints>
1. **引用优先**：除非用户明确要求关闭，否则必须在回答中包含笔记引用（来源: 库名 | 标题 | 内容）。
2. **逻辑连续性**：在处理复杂问题时，应先调用 biji.py 获取知识，严禁直接通过通用知识幻觉回答。
3. **环境安全**：严禁在日志或输出中暴露 API Key 或 Topic ID，配置信息应仅留存在本地 ~/.claude/ 目录下。
4. **状态感知**：在处理超过 3 步的复杂任务时，必须创建 search_plan.md 记录任务进度。
5. **范围继承**：追问时默认延续上一次的检索范围，除非用户显式指定新范围。
</constraints>

---

## Prerequisites（前置条件）

获取 API 凭证：
1. 访问 https://www.biji.com/subject
2. 进入目标知识库，点击 "API 设置"
3. 复制 **API Key** 和 **知识库 ID**

**重要**: API Key 是敏感信息，请勿提交到版本控制系统。

---

## Core Actions（核心操作）

### 1. 配置管理

```bash
# 添加知识库（首次配置）
python3 scripts/biji.py config add \
  --name "知识库名称" \
  --api-key "YOUR_API_KEY" \
  --topic-id "YOUR_TOPIC_ID" \
  --default

# 查看所有配置
python3 scripts/biji.py config list

# 设置全局引用开关
python3 scripts/biji.py config set refs true
```

### 2. 基础检索

```bash
# 简单搜索（使用默认知识库）
python3 scripts/biji.py search "你的问题"

# 指定知识库搜索
python3 scripts/biji.py search "问题" --kb "知识库名"

# 开启新会话（清除历史上下文）
python3 scripts/biji.py search "新话题" --new

# 关闭深度思考模式
python3 scripts/biji.py search "简单问题" --no-deep-seek
```

### 3. 检索范围控制

| 模式 | Flag | 执行逻辑 |
|------|------|----------|
| 默认模式 | `--default` | 仅查询 is_default 标记的库 |
| 精准模式 | `--kb "名称"` | 查询指定的单个或多个库 |
| 广播模式 | `--auto` | 语义路由，自动匹配描述相关的库 |
| 广域模式 | `--all` | 遍历所有已配置的知识库 |

**示例**:
```bash
# 默认库搜索
python3 scripts/biji.py search "房地产政策" --default

# 指定多个库搜索
python3 scripts/biji.py search "AI 趋势" --kb "技术笔记" --kb "投资参考"

# 自动路由（根据描述匹配最相关的库）
python3 scripts/biji.py search "最新政策分析" --auto

# 全库检索
python3 scripts/biji.py search "年度总结" --all

# 命令叠加
python3 scripts/biji.py search "新问题" --all --new
```

### 4. 追问与上下文

- **自动延续**：默认继承上一次检索的范围和会话
- **显式切换**：使用 `--new` 开启新会话，使用范围 Flag 切换检索范围
- **范围锁定**：切换后的追问会继承新范围

```bash
# 首次搜索（指定技术笔记库）
python3 scripts/biji.py search "什么是微服务？" --kb "技术笔记"

# 追问（自动延续在技术笔记库）
python3 scripts/biji.py search "它有什么优缺点？"

# 切换到全库（后续追问也在全库）
python3 scripts/biji.py search "其他领域如何应用？" --all
```

### 5. 召回原始数据

获取未经 AI 处理的检索结果，查看评分和来源信息：

```bash
python3 scripts/biji.py recall "问题" --top-k 10
```

---

## Advanced: Multi-KB Cross-Analysis（多库关联分析）

当用户提出跨领域或复杂问题时，必须启动"问题拆解-多库检索"模式。

### 工作流程

1. **任务建模**：将问题拆解为 2-4 个具体的原子搜索词
2. **执行检索**：调用 multi_search.py 或逐库执行 biji.py search
3. **关联分析**：对比不同库之间的知识关联、冲突或互补点

### 执行示例

```bash
# 使用 multi_search.py 执行跨库检索
python3 scripts/multi_search.py '{"queries": ["AI Agent 协作", "多智能体架构"], "kbs": ["政经参考", "技术笔记"]}'
```

### 关联分析模板

- **比较维度**：对比不同库中对同一概念的描述差异
- **发散关联**：寻找 A 库的理论在 B 库中的实践案例
- **冲突校验**：识别不同笔记之间的观点矛盾

---

## Task Planning (Manus 模式)

在处理需要多次搜索的复杂任务时，必须通过物理文件锚定任务进度：

### 启动条件

- 任务涉及 3 个以上检索步骤
- 需要跨库整合信息
- 用户要求深度分析或报告

### 执行流程

1. **建立物理规划**：在工作区创建 `search_plan.md`

```markdown
# 任务：[任务描述]
- 状态：进行中
- 检索目标：
  1. [ ] 搜索 [库A] 关于 [关键词1]
  2. [ ] 搜索 [库B] 关于 [关键词2]
  3. [ ] 整合分析并输出报告

## 检索记录
（每次搜索后在此记录结论）
```

2. **状态记录**：每完成一次搜索，将核心结论同步至 search_plan.md
3. **重大决策前重读**：在输出最终结论前，重新读取 search_plan.md 刷新注意力

---

## Tool & Script Integration（工具与脚本集成）

### 脚本清单

| 脚本 | 用途 |
|------|------|
| `scripts/biji.py` | 主程序入口（推荐使用） |
| `scripts/config_manager.py` | 配置管理模块 |
| `scripts/session_manager.py` | 会话管理模块 |
| `scripts/search_knowledge.py` | 底层搜索 API |
| `scripts/recall_knowledge.py` | 召回 API |
| `scripts/multi_search.py` | 多库联合查询 |
| `scripts/sync_metadata.py` | 自动描述生成 |

### 引用规范

所有引用必须包含三要素：

```
[结论内容] [来源: {库名} | 标题: {文章标题} | 核心: {内容摘要}]
```

### 详细 API 参考

完整的 API 文档请参阅 [references/api_reference.md](references/api_reference.md)

---

## API Limits（接口限制）

- **QPS**: 2 请求/秒
- **日调用上限**: 5,000 次

**最佳实践**:
1. 使用流式模式 (`--stream`) 获得更好的用户体验
2. 在多库检索时添加 0.5 秒间隔
3. 合理使用 `--new` 管理会话，避免上下文过长

---

## Troubleshooting（故障排除）

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| Authorization failed | API Key 错误 | 检查 API Key 是否正确 |
| Topic not found | 知识库 ID 错误 | 核实 Topic ID |
| Rate limit exceeded | 超出 QPS 限制 | 等待后重试 |
| No results | 无匹配内容 | 尝试不同关键词或使用 --intent-rewrite |

---

<!-- 末尾锚定：具体的执行指令与输出要求 -->
<final_instruction>
在向用户交付最终答案前，请核对：

1. **来源引用**：是否已为每条结论标注引用来源（库名 | 标题 | 内容）？
2. **范围确认**：当前检索范围是否符合用户预期？
3. **状态同步**：如果是复杂任务，search_plan.md 是否已更新？
4. **上下文刷新**：如果对话超过 10 轮，是否建议用户使用 --new 优化性能？
5. **一致性检查**：回答是否严格基于 API 返回的原始素材？

**输出格式**：[结论概要] + [引用的笔记列表] + [后续建议]

**冲突处理**：当多个库的信息出现矛盾时，必须在回复中显式列出不同来源的观点差异，禁止由模型私自平滑处理。
</final_instruction>
