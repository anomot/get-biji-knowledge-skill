#!/usr/bin/env python3
"""
Get笔记知识库搜索脚本 - AI 处理后的结果

使用方法:
    python3 search_knowledge.py --api-key YOUR_API_KEY --topic-id YOUR_TOPIC_ID --question "你的问题"
"""

import argparse
import requests
import json
import sys

def search_knowledge(api_key, topic_id, question, deep_seek=True, refs=False, history=None, stream=False):
    """
    搜索知识库并返回 AI 处理后的结果

    Args:
        api_key: API密钥
        topic_id: 知识库ID
        question: 搜索问题
        deep_seek: 是否开启深度思考
        refs: 是否返回引用
        history: 历史对话列表
        stream: 是否使用流式响应
    """
    base_url = "https://open-api.biji.com/getnote/openapi"
    endpoint = "/knowledge/search/stream" if stream else "/knowledge/search"
    url = base_url + endpoint

    headers = {
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "Authorization": f"Bearer {api_key}",
        "X-OAuth-Version": "1"
    }

    data = {
        "question": question,
        "topic_ids": [topic_id],
        "deep_seek": deep_seek,
        "refs": refs
    }

    if history:
        data["history"] = history

    try:
        if stream:
            # 流式响应
            response = requests.post(url, headers=headers, json=data, stream=True, timeout=120)
            response.raise_for_status()

            print("=== 流式响应 ===\n")
            full_answer = ""
            refs_data = None

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            json_data = json.loads(line_str[6:])
                            msg_type = json_data.get('msg_type')
                            data_content = json_data.get('data', {})
                            msg = data_content.get('msg', '')

                            if msg_type == 6:
                                # 处理流程
                                print(f"[流程] {msg}")
                            elif msg_type == 105:
                                # 引用数据
                                refs_data = data_content.get('ref_list', [])
                            elif msg_type == 21:
                                # 深度思考过程
                                print(msg, end='', flush=True)
                            elif msg_type == 22:
                                # 思考时长
                                print(f"\n[思考时长: {msg}ms]\n")
                            elif msg_type == 1:
                                # 回答内容
                                print(msg, end='', flush=True)
                                full_answer += msg
                            elif msg_type == 3:
                                # 结束
                                print("\n\n=== 回答完成 ===")
                            elif msg_type == 8:
                                # 风控提醒
                                print(f"\n[风控提醒: {msg}]")
                            elif msg_type == 0:
                                # 错误
                                print(f"\n[错误: {msg}]")
                        except json.JSONDecodeError:
                            continue

            if refs_data:
                print("\n\n=== 引用来源 ===")
                for i, ref in enumerate(refs_data, 1):
                    print(f"\n[{i}] {ref.get('title', '无标题')}")
                    print(f"    类型: {ref.get('rag_type', 'unknown')}")
                    print(f"    ID: {ref.get('note_id', '')}")

            return {"answer": full_answer, "refs": refs_data}
        else:
            # 非流式响应
            response = requests.post(url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            result = response.json()

            if result.get('h', {}).get('c') == 0:
                answer_data = result.get('c', {})
                print("=== 回答 ===\n")
                print(answer_data.get('answers', ''))

                if 'deep_seek' in answer_data:
                    print("\n\n=== 深度思考 ===\n")
                    print(answer_data.get('deep_seek', ''))

                return answer_data
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
        description='Get笔记知识库搜索 - AI处理后的结果',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    # 基础搜索
    python3 search_knowledge.py --api-key YOUR_KEY --topic-id YOUR_TOPIC --question "什么是AI?"

    # 开启引用
    python3 search_knowledge.py --api-key YOUR_KEY --topic-id YOUR_TOPIC --question "什么是AI?" --refs

    # 使用流式响应
    python3 search_knowledge.py --api-key YOUR_KEY --topic-id YOUR_TOPIC --question "什么是AI?" --stream

    # 带历史对话的追问
    python3 search_knowledge.py --api-key YOUR_KEY --topic-id YOUR_TOPIC --question "更详细呢?" --history '[{"content":"什么是AI","role":"user"},{"content":"AI是人工智能","role":"assistant"}]'
        '''
    )

    parser.add_argument('--api-key', required=True, help='Get笔记 API Key')
    parser.add_argument('--topic-id', required=True, help='知识库ID')
    parser.add_argument('--question', required=True, help='搜索问题')
    parser.add_argument('--deep-seek', action='store_true', default=True, help='开启深度思考（默认开启）')
    parser.add_argument('--no-deep-seek', action='store_false', dest='deep_seek', help='关闭深度思考')
    parser.add_argument('--refs', action='store_true', help='返回引用来源（仅stream模式生效）')
    parser.add_argument('--stream', action='store_true', help='使用流式响应')
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

    # 执行搜索
    result = search_knowledge(
        api_key=args.api_key,
        topic_id=args.topic_id,
        question=args.question,
        deep_seek=args.deep_seek,
        refs=args.refs,
        history=history,
        stream=args.stream
    )

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
