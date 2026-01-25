---
name: get-biji-knowledge
description: "Access and search Get笔记 (biji.com) knowledge bases using OpenAPI. Use when users need to (1) Search their Get笔记 knowledge base, (2) Query information from Get笔记, (3) Ask follow-up questions with conversation history, (4) Retrieve raw recall results for analysis. Supports deep thinking mode, reference citations, and streaming responses. Requires API Key and knowledge base ID from biji.com."
---

# Get笔记知识库 (Get Biji Knowledge)

Integrate Get笔记 knowledge bases into Claude Code workflows using the official OpenAPI.

> 🎯 **新用户？** 直接查看 [使用指南.md](使用指南.md) - 用大白话告诉你如何在对话框中使用这个技能！
>
> 💻 **技术用户？** 继续阅读下面的 Quick Start 和 Advanced Usage 部分。

## Overview

Get笔记 is an AI-powered knowledge management tool that helps users efficiently record, organize, and apply personal knowledge. This skill enables Claude to:

- **Search knowledge bases** with AI-processed results
- **Enable deep thinking** for complex queries
- **Get reference citations** for sources
- **Support follow-up questions** with conversation history (automatic context management)
- **Retrieve raw recall results** for detailed analysis
- **Auto-save results** to Markdown files in current directory

## Quick Start (Recommended)

**New user-friendly interface** - one-time setup, automatic context, clean output, Markdown export!

### Step 1: Configure Your Knowledge Base (One Time Only)

```bash
python3 scripts/biji.py config add \
  --name "我的笔记" \
  --api-key "YOUR_API_KEY" \
  --topic-id "YOUR_TOPIC_ID" \
  --default
```

Get your credentials from: https://www.biji.com/subject → API 设置

### Step 2: Search!

```bash
# Simple search (uses default knowledge base)
python3 scripts/biji.py search "你的问题"

# Specify knowledge base
python3 scripts/biji.py search "Python最佳实践" --kb "技术笔记"

# Start new conversation
python3 scripts/biji.py search "新话题" --new
```

**That's it!** The tool will:
- ✅ Remember your API credentials
- ✅ Automatically manage conversation context for follow-ups
- ✅ Save results as Markdown files in current directory
- ✅ Show clean, formatted output (no script details)

### View Your Configurations

```bash
# List all knowledge bases
python3 scripts/biji.py config list

# Show specific knowledge base
python3 scripts/biji.py config show "我的笔记"
```

### View Conversation History

```bash
# List all sessions
python3 scripts/biji.py session list

# List sessions for specific knowledge base
python3 scripts/biji.py session list --kb "技术笔记"
```

### Example Workflow

```bash
# First time: configure
python3 scripts/biji.py config add --name "工作笔记" --api-key sk_xxx --topic-id DMJa --default

# Ask first question
python3 scripts/biji.py search "什么是微服务架构？"
# → Saves to: get_工作笔记_20260125_143022.md

# Follow-up question (context automatically included)
python3 scripts/biji.py search "它有什么优缺点？"
# → Appends to: get_工作笔记_20260125_143022.md

# Start new topic
python3 scripts/biji.py search "Docker容器化部署流程" --new
# → Creates new session, saves to: get_工作笔记_20260125_150000.md
```

## Prerequisites

Before using this skill, obtain your API credentials:

1. Visit Get笔记 knowledge base: https://www.biji.com/subject
2. Navigate to the knowledge base you want to use
3. Click "API 设置" (API Settings) in the top navigation
4. Copy your **API Key** and **知识库 ID** (Topic ID)

**Important**: Keep your API Key secure. Never commit it to version control.

## Features

### 🎯 Easy Mode (scripts/biji.py) - **Recommended**

- ✅ One-time configuration (save API credentials)
- ✅ Automatic conversation context management
- ✅ Clean, user-friendly output
- ✅ Auto-save results to Markdown files
- ✅ No need to see Python script execution

```bash
# Configure once
python3 scripts/biji.py config add --name "我的笔记" --api-key KEY --topic-id ID --default

# Then just search
python3 scripts/biji.py search "你的问题"

# Follow-up questions work automatically (context preserved)
python3 scripts/biji.py search "更详细的内容？"
```

### ⚙️ Advanced Mode (Low-level API scripts)

For advanced users who need:
- Manual control over all parameters
- Integration with other tools
- Custom workflow automation

See [Advanced Usage](#advanced-usage) section below.

---

## Core Capabilities

### 1. AI-Powered Knowledge Search

Search your Get笔记 knowledge base with AI-processed, intelligently formatted results.

**When to use**:
- User asks to search their Get笔记 knowledge base
- Need intelligent answers synthesized from multiple sources
- Want deep thinking analysis for complex questions
- Need to see source references and citations

**How to use**:

```bash
python3 scripts/search_knowledge.py \
  --api-key YOUR_API_KEY \
  --topic-id YOUR_TOPIC_ID \
  --question "你的问题" \
  --stream \
  --refs
```

**Parameters**:
- `--api-key`: Your Get笔记 API Key (required)
- `--topic-id`: Knowledge base ID (required)
- `--question`: Search query (required)
- `--stream`: Enable streaming responses for real-time output (recommended)
- `--refs`: Include source references and citations
- `--deep-seek` / `--no-deep-seek`: Enable/disable deep thinking mode (default: enabled)
- `--history`: JSON string for follow-up questions

**Example workflow**:

```
User: "Search my Get笔记 for information about machine learning algorithms"

# First, ask the user for their credentials if not already provided
Assistant: "To search your Get笔记 knowledge base, I'll need your API Key and Topic ID. You can find these at https://www.biji.com/subject > API Settings."

User: [Provides API_KEY and TOPIC_ID]

# Run the search
python3 scripts/search_knowledge.py \
  --api-key USER_API_KEY \
  --topic-id USER_TOPIC_ID \
  --question "machine learning algorithms" \
  --stream \
  --refs

# The script will output:
# - Processing status
# - Deep thinking process
# - Answer content
# - Reference citations
```

### 2. Follow-up Questions with Context

Continue a conversation by passing previous Q&A as history.

**When to use**:
- User asks a follow-up question
- Need to refine or clarify previous answers
- Want to explore a topic in more depth

**How to use**:

```bash
# First question
python3 scripts/search_knowledge.py \
  --api-key YOUR_API_KEY \
  --topic-id YOUR_TOPIC_ID \
  --question "什么是深度学习？"

# Follow-up question with history
python3 scripts/search_knowledge.py \
  --api-key YOUR_API_KEY \
  --topic-id YOUR_TOPIC_ID \
  --question "它和机器学习有什么区别？" \
  --history '[{"content":"什么是深度学习？","role":"user"},{"content":"深度学习是一种机器学习方法...","role":"assistant"}]'
```

**Note**: Build the history array incrementally with each question-answer pair.

### 3. Raw Recall Results

Retrieve unprocessed recall results to see detailed scoring and source information.

**When to use**:
- Need to understand which documents were retrieved
- Want to see similarity scores and ranking
- Debugging or analyzing search quality
- Need raw content without AI processing

**How to use**:

```bash
python3 scripts/recall_knowledge.py \
  --api-key YOUR_API_KEY \
  --topic-id YOUR_TOPIC_ID \
  --question "你的问题" \
  --top-k 5 \
  --intent-rewrite \
  --select-matrix
```

**Parameters**:
- `--api-key`: Your Get笔记 API Key (required)
- `--topic-id`: Knowledge base ID (required)
- `--question`: Search query (required)
- `--top-k`: Number of results to return (default: 10)
- `--intent-rewrite`: Enable question intent rewriting
- `--select-matrix`: Enable result re-ranking
- `--history`: JSON string for follow-up questions

**Output includes**:
- Document ID
- Title
- Content preview
- Similarity score
- Source type (FILE, NOTE, BLOGGER)
- Recall source (embedding, keyword)

## API Limits and Best Practices

**Current API Limits** (Public Beta):
- QPS: 2 requests per second
- Daily limit: 5,000 calls

**Best Practices**:

1. **Use streaming mode** (`--stream`) for better user experience
2. **Enable refs** when citations are important
3. **Cache credentials** - don't ask repeatedly for API keys
4. **Handle errors gracefully** - check for rate limits and failures
5. **Batch related questions** to minimize API calls

## Detailed Reference

For comprehensive API documentation, including:
- Complete endpoint specifications
- Response format details
- Error codes and handling
- Advanced configuration options

See [references/api_reference.md](references/api_reference.md)

## Troubleshooting

**"Authorization failed"**:
- Verify API Key is correct
- Check that X-OAuth-Version header is set to "1"

**"Topic not found"**:
- Verify Topic ID matches your knowledge base
- Ensure knowledge base has API access enabled

**"Rate limit exceeded"**:
- Current QPS is 2, wait before retrying
- Daily limit is 5,000 calls

**"No results returned"**:
- Try different search terms
- Check if knowledge base has relevant content
- Use `--intent-rewrite` for better query understanding

## Getting Help

- Get笔记 Web: https://www.biji.com/subject
- API Settings: Click "API 设置" in knowledge base view
- Official support: Join Get笔记 support group (QR code in official docs)

---

## Advanced Usage

For users who need direct API access and manual control.

### Direct API Scripts

The following low-level scripts are available for advanced use cases:

#### 1. search_knowledge.py - Direct API Search

Manual API search with full parameter control:

```bash
python3 scripts/search_knowledge.py \
  --api-key YOUR_API_KEY \
  --topic-id YOUR_TOPIC_ID \
  --question "你的问题" \
  --stream \
  --refs \
  --deep-seek
```

**When to use**: Custom integrations, automation, specific parameter tuning.

#### 2. recall_knowledge.py - Raw Recall API

Get unprocessed recall results:

```bash
python3 scripts/recall_knowledge.py \
  --api-key YOUR_API_KEY \
  --topic-id YOUR_TOPIC_ID \
  --question "你的问题" \
  --top-k 10 \
  --intent-rewrite \
  --select-matrix
```

**When to use**: Debugging, analyzing search quality, building custom processing.

#### 3. Manual Context Management

Pass history manually for follow-up questions:

```bash
python3 scripts/search_knowledge.py \
  --api-key YOUR_API_KEY \
  --topic-id YOUR_TOPIC_ID \
  --question "追问内容" \
  --history '[{"content":"第一个问题","role":"user"},{"content":"回答","role":"assistant"}]'
```

### Configuration and Session Management Utilities

```bash
# Configuration management
python3 scripts/config_manager.py add --name "笔记" --api-key KEY --topic-id ID
python3 scripts/config_manager.py list
python3 scripts/config_manager.py show "笔记"

# Session management
python3 scripts/session_manager.py list --kb "笔记"
python3 scripts/session_manager.py show SESSION_ID
python3 scripts/session_manager.py clear SESSION_ID
```

### Integration Example

Example of integrating into a custom script:

```python
import sys
sys.path.insert(0, '/path/to/scripts')

from config_manager import ConfigManager
from session_manager import SessionManager

# Load config
config_mgr = ConfigManager()
config = config_mgr.get_knowledge_base("我的笔记")

# Use the API
# ... your custom code here
```

**Note**: For most use cases, `biji.py` is the recommended interface. Use these advanced scripts only when you need specific customization.
