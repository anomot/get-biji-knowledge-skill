#!/usr/bin/env python3
"""
Get笔记知识库查询工具 - 优化版本

核心特性:
- 同一会话的问答累积保存到同一个文件
- 自动生成问答记录和引用记录两个文件
- 支持全局引用开关设置
- 一个 API Key 可用于多个仓库
"""

import sys
import os
import argparse
import requests
import json
from pathlib import Path
from datetime import datetime

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from config_manager import ConfigManager
from session_manager import SessionManager


class BijiClient:
    def __init__(self, output_dir=None):
        self.config_manager = ConfigManager()
        self.session_manager = SessionManager()
        # 优先级: 环境变量 > 参数 > 当前工作目录
        if output_dir:
            self.output_dir = Path(output_dir)
        elif os.environ.get('BIJI_OUTPUT_DIR'):
            self.output_dir = Path(os.environ.get('BIJI_OUTPUT_DIR'))
        else:
            self.output_dir = Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 会话文件追踪
        self.current_qa_file = None
        self.current_refs_file = None
        self.session_start_time = None

    def search(self, question, knowledge_base=None, new_session=False, deep_seek=True, refs=None):
        """搜索知识库"""
        # 获取配置
        config = self.config_manager.get_knowledge_base(knowledge_base)
        if not config:
            kb_name = knowledge_base or "默认"
            print(f"❌ 错误: 知识库 '{kb_name}' 未配置")
            print(f"\n请先添加配置:")
            print(f"  python3 biji.py config add --name 我的笔记 --api-key YOUR_KEY --topic-id YOUR_ID")
            return None

        kb_name = knowledge_base or self.config_manager.get_default()

        # 使用全局 refs 设置（如果用户没有指定）
        if refs is None:
            refs = self.config_manager.get_global_setting('refs', True)

        # 管理会话
        if new_session:
            session_id = self.session_manager.new_session(kb_name)
            print(f"🆕 创建新会话: {session_id}\n")
            # 重置文件追踪
            self.current_qa_file = None
            self.current_refs_file = None
            self.session_start_time = datetime.now()
        else:
            session_id = self.session_manager.get_latest_session(kb_name)
            if not session_id:
                session_id = self.session_manager.new_session(kb_name)
                print(f"🆕 创建新会话: {session_id}\n")
                self.current_qa_file = None
                self.current_refs_file = None
                self.session_start_time = datetime.now()
            else:
                print(f"📖 继续会话: {session_id}\n")
                # 继续使用现有会话的文件
                if self.session_start_time is None:
                    self.session_start_time = datetime.now()

        # 准备请求
        url = "https://open-api.biji.com/getnote/openapi/knowledge/search/stream"
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Authorization": f"Bearer {config['api_key']}",
            "X-OAuth-Version": "1"
        }

        data = {
            "question": question,
            "topic_ids": [config['topic_id']],
            "deep_seek": deep_seek,
            "refs": refs,
            "history": self.session_manager.get_history()
        }

        print(f"💭 问题: {question}\n")
        print("=" * 60)

        try:
            response = requests.post(url, headers=headers, json=data, stream=True, timeout=120)
            response.raise_for_status()

            full_answer = ""
            refs_data = []
            thinking_content = ""

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
                                pass  # 处理流程 - 静默
                            elif msg_type == 105:
                                refs_data = data_content.get('ref_list', [])
                            elif msg_type == 21:
                                thinking_content += msg
                            elif msg_type == 22:
                                pass  # 思考时长 - 静默
                            elif msg_type == 1:
                                print(msg, end='', flush=True)
                                full_answer += msg
                            elif msg_type == 3:
                                print("\n" + "=" * 60)
                            elif msg_type == 8:
                                print(f"\n⚠️ 提醒: {msg}")
                            elif msg_type == 0:
                                print(f"\n❌ 错误: {msg}")
                                return None
                        except json.JSONDecodeError:
                            continue

            # 保存到会话历史
            self.session_manager.add_turn(question, full_answer)

            # 累积保存到 Markdown 文件
            self._append_to_session_files(
                question, full_answer, refs_data, thinking_content,
                kb_name, session_id
            )

            # 显示文件保存信息
            if self.current_qa_file:
                print(f"\n📄 问答已保存到: {self.current_qa_file.name}")
            if self.current_refs_file and refs_data:
                print(f"📚 引用已保存到: {self.current_refs_file.name}")

            return {
                "answer": full_answer,
                "refs": refs_data,
                "thinking": thinking_content,
                "session_id": session_id
            }

        except requests.exceptions.RequestException as e:
            print(f"\n❌ 请求失败: {e}")
            return None
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            return None

    def _append_to_session_files(self, question, answer, refs, thinking, kb_name, session_id):
        """累积追加内容到会话文件"""
        timestamp = self.session_start_time or datetime.now()
        base_filename = f"get_{kb_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # 初始化问答文件（首次）
        if self.current_qa_file is None:
            self.current_qa_file = self.output_dir / f"{base_filename}.md"

            # 写入问答文件头部
            with open(self.current_qa_file, 'w', encoding='utf-8') as f:
                f.write(f"# Get笔记查询记录\n\n")
                f.write(f"**知识库**: {kb_name}\n")
                f.write(f"**会话ID**: {session_id}\n")
                f.write(f"**开始时间**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")

        # 追加问答内容
        current_time = datetime.now().strftime('%H:%M:%S')
        with open(self.current_qa_file, 'a', encoding='utf-8') as f:
            f.write(f"## 问题 [{current_time}]\n\n")
            f.write(f"{question}\n\n")
            f.write(f"## 回答\n\n")
            f.write(f"{answer}\n\n")

            if thinking:
                f.write(f"### 深度思考过程\n\n")
                f.write(f"```\n{thinking}\n```\n\n")

            # 添加引用来源列表
            if refs:
                f.write(f"### 📚 引用来源\n\n")
                for i, ref in enumerate(refs, 1):
                    f.write(f"[{i}] {ref.get('title', '无标题')}\n")
                f.write(f"\n> 详细引用内容请查看：{base_filename}_引用.md\n\n")

            f.write("---\n\n")

        # 追加引用内容（只在有引用数据时）
        if refs:
            # 初始化引用文件（首次且有引用数据时）
            if self.current_refs_file is None:
                self.current_refs_file = self.output_dir / f"{base_filename}_引用.md"

                # 写入引用文件头部
                with open(self.current_refs_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Get笔记引用记录\n\n")
                    f.write(f"**知识库**: {kb_name}\n")
                    f.write(f"**会话ID**: {session_id}\n")
                    f.write(f"**开始时间**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")

            # 追加引用详细内容
            with open(self.current_refs_file, 'a', encoding='utf-8') as f:
                f.write(f"## 问题: {question} [{current_time}]\n\n")

                for i, ref in enumerate(refs, 1):
                    f.write(f"### [{i}] {ref.get('title', '无标题')}\n\n")
                    f.write(f"- **类型**: {ref.get('rag_type', 'unknown')}\n")
                    f.write(f"- **笔记ID**: {ref.get('note_id', '')}\n\n")

                    details = ref.get('detail', [])
                    if details:
                        f.write(f"**详细内容**:\n\n")
                        for detail in details:
                            content = detail.get('content', '')
                            if content:
                                f.write(f"> {content}\n\n")

                    f.write("\n")

                f.write("---\n\n")

    def recall(self, question, knowledge_base=None, top_k=10):
        """获取原始召回结果"""
        config = self.config_manager.get_knowledge_base(knowledge_base)
        if not config:
            kb_name = knowledge_base or "默认"
            print(f"❌ 错误: 知识库 '{kb_name}' 未配置")
            return None

        url = "https://open-api.biji.com/getnote/openapi/knowledge/search/recall"
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Authorization": f"Bearer {config['api_key']}",
            "X-OAuth-Version": "1"
        }

        data = {
            "question": question,
            "topic_id": config['topic_id'],
            "top_k": top_k
        }

        print(f"🔍 召回查询: {question}\n")
        print("=" * 60)

        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()

            if result.get('h', {}).get('c') == 0:
                recall_data = result.get('c', {}).get('data', [])
                print(f"\n📊 找到 {len(recall_data)} 条相关结果:\n")

                for i, item in enumerate(recall_data, 1):
                    print(f"[{i}] {item.get('title', '无标题')}")
                    print(f"    📈 得分: {item.get('score', 0):.4f}")
                    print(f"    📁 类型: {item.get('type', 'unknown')}")
                    print(f"    🔗 来源: {item.get('recall_source', 'unknown')}")

                    content = item.get('content', '')
                    if content:
                        preview = content[:150].replace('\n', ' ')
                        if len(content) > 150:
                            preview += "..."
                        print(f"    📝 内容: {preview}")
                    print()

                print("=" * 60)
                return recall_data
            else:
                error_msg = result.get('h', {}).get('e', '未知错误')
                print(f"❌ 错误: {error_msg}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")
            return None
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description='Get笔记知识库查询工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    # 配置知识库（一个 API Key 可用于多个仓库）
    python3 biji.py config add --name 政经参考 --api-key YOUR_KEY --topic-id ID1 --default
    python3 biji.py config add --name 技术笔记 --api-key YOUR_KEY --topic-id ID2
    python3 biji.py config add --name 学习笔记 --api-key YOUR_KEY --topic-id ID3

    # 搜索（默认仓库）
    python3 biji.py search "你的问题"

    # 搜索指定仓库
    python3 biji.py search "技术问题" --kb 技术笔记

    # 新会话搜索
    python3 biji.py search "新话题" --new

    # 设置全局引用开关
    python3 biji.py config set refs true   # 开启引用
    python3 biji.py config set refs false  # 关闭引用

    # 查看配置
    python3 biji.py config list
        '''
    )

    parser.add_argument('--output', '-o', help='输出目录（默认当前目录）')

    subparsers = parser.add_subparsers(dest='command', help='命令')

    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索知识库')
    search_parser.add_argument('question', help='搜索问题')
    search_parser.add_argument('--kb', help='知识库名称（默认使用默认知识库）')
    search_parser.add_argument('--new', action='store_true', help='创建新会话')
    search_parser.add_argument('--no-deep-seek', action='store_false', dest='deep_seek', help='关闭深度思考')
    search_parser.add_argument('--refs', type=lambda x: x.lower() == 'true', help='是否显示引用（true/false）')

    # recall 命令
    recall_parser = subparsers.add_parser('recall', help='查看原始召回结果')
    recall_parser.add_argument('question', help='搜索问题')
    recall_parser.add_argument('--kb', help='知识库名称')
    recall_parser.add_argument('--top-k', type=int, default=10, help='返回结果数量')

    # config 命令
    config_parser = subparsers.add_parser('config', help='管理配置')
    config_subparsers = config_parser.add_subparsers(dest='config_command')

    config_add = config_subparsers.add_parser('add', help='添加知识库')
    config_add.add_argument('--name', required=True, help='知识库名称')
    config_add.add_argument('--api-key', required=True, help='API Key（可多个仓库共用）')
    config_add.add_argument('--topic-id', required=True, help='知识库ID')
    config_add.add_argument('--default', action='store_true', help='设为默认')

    config_list = config_subparsers.add_parser('list', help='列出所有知识库')

    config_show = config_subparsers.add_parser('show', help='显示知识库配置')
    config_show.add_argument('name', nargs='?', help='知识库名称')

    config_set = config_subparsers.add_parser('set', help='设置全局选项')
    config_set.add_argument('key', help='选项名称（如 refs）')
    config_set.add_argument('value', help='选项值（true/false）')

    config_default = config_subparsers.add_parser('default', help='设置默认知识库')
    config_default.add_argument('name', help='知识库名称')

    # session 命令
    session_parser = subparsers.add_parser('session', help='管理会话')
    session_subparsers = session_parser.add_subparsers(dest='session_command')

    session_list = session_subparsers.add_parser('list', help='列出会话')
    session_list.add_argument('--kb', help='知识库名称')

    session_clear = session_subparsers.add_parser('clear', help='清空会话')
    session_clear.add_argument('session_id', help='会话ID')

    args = parser.parse_args()

    # 创建客户端
    client = BijiClient(args.output if hasattr(args, 'output') and args.output else None)

    if args.command == 'search':
        client.search(
            args.question,
            knowledge_base=args.kb,
            new_session=args.new,
            deep_seek=args.deep_seek,
            refs=args.refs
        )

    elif args.command == 'recall':
        client.recall(
            args.question,
            knowledge_base=args.kb,
            top_k=args.top_k
        )

    elif args.command == 'config':
        config_mgr = client.config_manager

        if args.config_command == 'add':
            config_mgr.add_knowledge_base(args.name, args.api_key, args.topic_id, args.default)
            print(f"✅ 已添加知识库: {args.name}")
            if args.default:
                print(f"⭐ 已设为默认知识库")

        elif args.config_command == 'list':
            bases = config_mgr.list_knowledge_bases()
            default = config_mgr.get_default()
            global_refs = config_mgr.get_global_setting('refs', True)

            print("📚 已配置的知识库:\n")
            for name in bases:
                prefix = "⭐" if name == default else "  "
                print(f"{prefix} {name}")
            if not bases:
                print("  (无)")
                print("\n提示: 使用 'config add' 添加知识库")

            print(f"\n⚙️  全局设置:")
            print(f"   引用显示: {'开启' if global_refs else '关闭'}")

        elif args.config_command == 'show':
            config = config_mgr.get_knowledge_base(args.name)
            if config:
                name = args.name or config_mgr.get_default()
                is_default = (name == config_mgr.get_default())
                print(f"📖 知识库: {name}")
                if is_default:
                    print(f"   状态: ⭐ 默认知识库")
                print(f"   API Key: {config['api_key'][:10]}...")
                print(f"   Topic ID: {config['topic_id']}")
            else:
                print("❌ 知识库不存在")

        elif args.config_command == 'set':
            if args.key == 'refs':
                value = args.value.lower() == 'true'
                config_mgr.set_global_setting('refs', value)
                print(f"✅ 全局引用显示已设置为: {'开启' if value else '关闭'}")
            else:
                print(f"❌ 未知的配置项: {args.key}")

        elif args.config_command == 'default':
            if config_mgr.set_default(args.name):
                print(f"✅ 默认知识库已设为: {args.name}")
            else:
                print(f"❌ 知识库不存在: {args.name}")

        else:
            config_parser.print_help()

    elif args.command == 'session':
        session_mgr = client.session_manager

        if args.session_command == 'list':
            sessions = session_mgr.list_sessions(args.kb)
            print(f"💬 会话列表:\n")
            for session in sessions:
                print(f"  {session['id']}")
                print(f"     创建时间: {session['created_at']}")
                print(f"     对话轮数: {session['turns']}")
                print()
            if not sessions:
                print("  (无)")

        elif args.session_command == 'clear':
            if session_mgr.load_session(args.session_id):
                session_mgr.clear_history()
                print(f"✅ 已清空会话: {args.session_id}")
            else:
                print(f"❌ 会话不存在: {args.session_id}")

        else:
            session_parser.print_help()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
