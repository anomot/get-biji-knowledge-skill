# Get笔记知识库 OpenAPI 参考文档

## 基本信息

- **接口基地址**: `https://open-api.biji.com/getnote/openapi`
- **认证方式**: Bearer Token Authentication
- **API 限制**:
  - QPS: 2
  - 日调用上限: 5000次

## 请求头

所有请求必须包含以下 Headers:

```
Content-Type: application/json
Connection: keep-alive
Authorization: Bearer {api-key}
X-OAuth-Version: 1
```

## API 端点

### 1. 知识库搜索接口 (AI处理后的结果)

**端点**: `/knowledge/search` 或 `/knowledge/search/stream`

**方法**: POST

**说明**: 经过 AI 处理后的结果信息，支持深度思考和引用返回。

**请求参数**:

| 字段 | 类型 | 必须 | 说明 | 默认值 |
|------|------|------|------|--------|
| question | string | 是 | 搜索问题 | - |
| topic_ids | []string | 是 | 知识库ID列表（当前只支持1个） | - |
| deep_seek | bool | 是 | 是否开启深度思考 | true |
| refs | bool | 否 | 是否返回引用（仅stream模式） | false |
| history | []object | 否 | 历史对话，用于追问 | null |

**history 格式**:

```json
[
  {
    "content": "什么是AI?",
    "role": "user"
  },
  {
    "content": "AI是人工智能",
    "role": "assistant"
  }
]
```

**Stream 响应的 msg_type**:

| msg_type | 说明 |
|----------|------|
| 6 | 处理流程状态 |
| 105 | 引用数据 |
| 21 | 深度思考过程 |
| 22 | 思考时长（毫秒） |
| 1 | 回答内容 |
| 3 | 结束标记 |
| 8 | 风控提醒 |
| 0 | 错误信息 |

### 2. 知识库召回接口 (原始召回结果)

**端点**: `/knowledge/search/recall`

**方法**: POST

**说明**: 未经 AI 处理的原始召回结果，可以看到召回的详细信息（得分、来源等）。

**请求参数**:

| 字段 | 类型 | 必须 | 说明 | 默认值 |
|------|------|------|------|--------|
| question | string | 是 | 搜索问题 | - |
| topic_id | string | 是* | 知识库ID | - |
| topic_ids | []string | 是* | 知识库ID列表 | - |
| top_k | int | 否 | 返回最相似的N个结果 | 10 |
| intent_rewrite | bool | 否 | 是否进行问题意图重写 | false |
| select_matrix | bool | 否 | 是否对结果进行重选 | false |
| history | []object | 否 | 历史对话 | null |

*注: topic_id 和 topic_ids 参数必须有一个不为空，优先使用 topic_id。

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 召回对应资源ID |
| title | string | 召回对应资源标题 |
| content | string | 召回内容 |
| score | float | 相似度得分 |
| type | string | 资源类型：FILE（文件）、NOTE（笔记）、BLOGGER（订阅博主或直播） |
| recall_source | string | 召回来源：embedding、keyword |

## 获取配置信息

1. 打开 Get 笔记知识库 Web 版本: https://www.biji.com/subject
2. 进入需要配置的知识库
3. 点击顶部的"API 设置"按钮
4. 获取知识库 ID 和 API Key

## 使用注意事项

1. **公测期说明**: 目前 API 处于免审公测期，所有功能可能随时调整
2. **历史对话**: history 参数已简化，无需传递即可正常使用
3. **Stream 模式**: 建议使用 stream 模式获取实时响应和引用数据
4. **速率限制**: 注意 QPS 和日调用限制，避免频繁调用

## 错误处理

检查响应中的 `h.c` 字段:
- `c == 0`: 请求成功
- `c != 0`: 请求失败，查看 `h.e` 字段获取错误信息
