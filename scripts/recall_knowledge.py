#!/usr/bin/env python3
"""
Get笔记知识库召回脚本 - 未经AI处理的原始召回结果

使用方法:
    python3 recall_knowledge.py --api-key YOUR_API_KEY --topic-id YOUR_TOPIC_ID --question "你的问题"
"""

import argparse
import requests
import json
import sys

def recall_knowledge(api_key, topic_id, question, top_k=10, intent_rewrite=False,
                     select_matrix=False, history=None):
    """
    召回知识库原始结果

    Args:
        api_key: API密钥
        topic_id: 知识库ID
        question: 搜索问题
        top_k: 返回最相似的N个结果
        intent_rewrite: 是否进行问题意图重写
        select_matrix: 是否对结果进行重选
        history: 历史对话列表
    """
    url = "https://open-api.biji.com/getnote/openapi/knowledge/search/recall"

    headers = {
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "Authorization": f"Bearer {api_key}",
        "X-OAuth-Version": "1"
    }

    data = {
        "question": question,
        "topic_id": topic_id,
        "top_k": top_k,
        "intent_rewrite": intent_rewrite,
        "select_matrix": select_matrix
    }

    if history:
        data["history"] = history

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()

        if result.get('h', {}).get('c') == 0:
            recall_data = result.get('c', {}).get('data', [])

            print(f"=== 召回结果 (共 {len(recall_data)} 条) ===\n")

            for i, item in enumerate(recall_data, 1):
                print(f"[{i}] {item.get('title', '无标题')}")
                print(f"    类型: {item.get('type', 'unknown')}")
                print(f"    得分: {item.get('score', 0):.4f}")
                print(f"    召回来源: {item.get('recall_source', 'unknown')}")
                print(f"    ID: {item.get('id', '')}")

                content = item.get('content', '')
                if content:
                    # 显示内容摘要（前200字符）
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"    内容: {content_preview}")

                print()

            return recall_data
        else:
            error_msg = result.get('h', {}).get('e', '未知错误')
            print(f"错误: {error_msg}", file=sys.stderr)
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"发生错误: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Get笔记知识库召回 - 未经AI处理的原始结果',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    # 基础召回
    python3 recall_knowledge.py --api-key YOUR_KEY --topic-id YOUR_TOPIC --question "什么是AI?"

    # 返回前5个最相似结果
    python3 recall_knowledge.py --api-key YOUR_KEY --topic-id YOUR_TOPIC --question "什么是AI?" --top-k 5

    # 开启意图重写和结果重选
    python3 recall_knowledge.py --api-key YOUR_KEY --topic-id YOUR_TOPIC --question "什么是AI?" --intent-rewrite --select-matrix

    # 带历史对话
    python3 recall_knowledge.py --api-key YOUR_KEY --topic-id YOUR_TOPIC --question "更详细呢?" --history '[{"content":"什么是AI","role":"user"},{"content":"AI是人工智能","role":"assistant"}]'
        '''
    )

    parser.add_argument('--api-key', required=True, help='Get笔记 API Key')
    parser.add_argument('--topic-id', required=True, help='知识库ID')
    parser.add_argument('--question', required=True, help='搜索问题')
    parser.add_argument('--top-k', type=int, default=10, help='返回最相似的N个结果（默认10）')
    parser.add_argument('--intent-rewrite', action='store_true', help='开启问题意图重写')
    parser.add_argument('--select-matrix', action='store_true', help='对结果进行重选')
    parser.add_argument('--history', type=str, help='历史对话JSON字符串')

    args = parser.parse_args()

    # 解析历史对话
    history = None
    if args.history:
        try:
            history = json.loads(args.history)
        except json.JSONDecodeError:
            print("错误: history 参数必须是有效的JSON字符串", file=sys.stderr)
            sys.exit(1)

    # 执行召回
    result = recall_knowledge(
        api_key=args.api_key,
        topic_id=args.topic_id,
        question=args.question,
        top_k=args.top_k,
        intent_rewrite=args.intent_rewrite,
        select_matrix=args.select_matrix,
        history=history
    )

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
