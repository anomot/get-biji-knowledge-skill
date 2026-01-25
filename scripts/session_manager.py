#!/usr/bin/env python3
"""
Get笔记会话管理器
自动管理对话上下文
"""

import json
import os
from pathlib import Path
from datetime import datetime

class SessionManager:
    def __init__(self, session_dir=None):
        if session_dir is None:
            # 默认会话目录：~/.claude/skills/get-biji-knowledge/sessions/
            home = Path.home()
            self.session_dir = home / ".claude" / "skills" / "get-biji-knowledge" / "sessions"
        else:
            self.session_dir = Path(session_dir)

        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.current_session = None
        self.history = []

    def new_session(self, knowledge_base_name):
        """创建新会话"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session = f"{knowledge_base_name}_{timestamp}"
        self.history = []
        return self.current_session

    def load_session(self, session_id):
        """加载已有会话"""
        session_file = self.session_dir / f"{session_id}.json"
        if session_file.exists():
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.current_session = session_id
                self.history = data.get("history", [])
                return True
        return False

    def get_latest_session(self, knowledge_base_name):
        """获取指定知识库的最新会话"""
        sessions = sorted(
            [f for f in self.session_dir.glob(f"{knowledge_base_name}_*.json")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if sessions:
            session_id = sessions[0].stem
            self.load_session(session_id)
            return session_id
        return None

    def add_turn(self, question, answer):
        """添加一轮对话"""
        self.history.append({
            "content": question,
            "role": "user"
        })
        self.history.append({
            "content": answer,
            "role": "assistant"
        })
        self._save_session()

    def get_history(self):
        """获取对话历史"""
        return self.history

    def clear_history(self):
        """清空当前会话历史"""
        self.history = []
        if self.current_session:
            self._save_session()

    def _save_session(self):
        """保存会话"""
        if self.current_session:
            session_file = self.session_dir / f"{self.current_session}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "session_id": self.current_session,
                    "created_at": datetime.now().isoformat(),
                    "history": self.history
                }, f, ensure_ascii=False, indent=2)

    def list_sessions(self, knowledge_base_name=None):
        """列出会话"""
        pattern = f"{knowledge_base_name}_*.json" if knowledge_base_name else "*.json"
        sessions = []
        for session_file in self.session_dir.glob(pattern):
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sessions.append({
                    "id": data["session_id"],
                    "created_at": data.get("created_at"),
                    "turns": len(data.get("history", [])) // 2
                })
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)

    def delete_session(self, session_id):
        """删除会话"""
        session_file = self.session_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
            if self.current_session == session_id:
                self.current_session = None
                self.history = []
            return True
        return False


if __name__ == "__main__":
    # 测试代码
    import argparse

    parser = argparse.ArgumentParser(description='Get笔记会话管理')
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # list 命令
    list_parser = subparsers.add_parser('list', help='列出会话')
    list_parser.add_argument('--kb', help='知识库名称')

    # show 命令
    show_parser = subparsers.add_parser('show', help='显示会话内容')
    show_parser.add_argument('session_id', help='会话ID')

    # delete 命令
    delete_parser = subparsers.add_parser('delete', help='删除会话')
    delete_parser.add_argument('session_id', help='会话ID')

    # clear 命令
    clear_parser = subparsers.add_parser('clear', help='清空当前会话')
    clear_parser.add_argument('session_id', help='会话ID')

    args = parser.parse_args()

    manager = SessionManager()

    if args.command == 'list':
        sessions = manager.list_sessions(args.kb)
        print(f"💬 会话列表:\n")
        for session in sessions:
            print(f"  {session['id']}")
            print(f"     创建时间: {session['created_at']}")
            print(f"     对话轮数: {session['turns']}")
            print()

    elif args.command == 'show':
        if manager.load_session(args.session_id):
            print(f"💬 会话: {args.session_id}\n")
            history = manager.get_history()
            for i in range(0, len(history), 2):
                if i < len(history):
                    print(f"👤 问: {history[i]['content']}")
                if i + 1 < len(history):
                    print(f"🤖 答: {history[i+1]['content'][:100]}...")
                print()
        else:
            print(f"❌ 会话不存在: {args.session_id}")

    elif args.command == 'delete':
        if manager.delete_session(args.session_id):
            print(f"✅ 已删除会话: {args.session_id}")
        else:
            print(f"❌ 会话不存在: {args.session_id}")

    elif args.command == 'clear':
        if manager.load_session(args.session_id):
            manager.clear_history()
            print(f"✅ 已清空会话: {args.session_id}")
        else:
            print(f"❌ 会话不存在: {args.session_id}")

    else:
        parser.print_help()
