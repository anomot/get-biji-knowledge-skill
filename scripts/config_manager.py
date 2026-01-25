#!/usr/bin/env python3
"""
Get笔记配置管理器
管理多个知识库的 API 凭证
"""

import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self, config_file=None):
        if config_file is None:
            # 默认配置文件路径：~/.claude/skills/get-biji-knowledge/config.json
            home = Path.home()
            config_dir = home / ".claude" / "skills" / "get-biji-knowledge"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / "config.json"
        else:
            self.config_file = Path(config_file)

        self.config = self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"knowledge_bases": {}, "default": None, "global_settings": {}}

    def _save_config(self):
        """保存配置文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def add_knowledge_base(self, name, api_key, topic_id, set_default=False):
        """添加知识库配置"""
        self.config["knowledge_bases"][name] = {
            "api_key": api_key,
            "topic_id": topic_id
        }
        if set_default or self.config["default"] is None:
            self.config["default"] = name
        self._save_config()
        return True

    def get_knowledge_base(self, name=None):
        """获取知识库配置"""
        if name is None:
            name = self.config["default"]

        if name is None:
            return None

        return self.config["knowledge_bases"].get(name)

    def list_knowledge_bases(self):
        """列出所有知识库"""
        return list(self.config["knowledge_bases"].keys())

    def set_default(self, name):
        """设置默认知识库"""
        if name in self.config["knowledge_bases"]:
            self.config["default"] = name
            self._save_config()
            return True
        return False

    def get_default(self):
        """获取默认知识库名称"""
        return self.config["default"]

    def remove_knowledge_base(self, name):
        """删除知识库配置"""
        if name in self.config["knowledge_bases"]:
            del self.config["knowledge_bases"][name]
            if self.config["default"] == name:
                # 如果删除的是默认知识库，选择第一个作为新默认
                bases = list(self.config["knowledge_bases"].keys())
                self.config["default"] = bases[0] if bases else None
            self._save_config()
            return True
        return False

    def get_global_setting(self, key, default=None):
        """获取全局设置"""
        if "global_settings" not in self.config:
            self.config["global_settings"] = {}
        return self.config["global_settings"].get(key, default)

    def set_global_setting(self, key, value):
        """设置全局选项"""
        if "global_settings" not in self.config:
            self.config["global_settings"] = {}
        self.config["global_settings"][key] = value
        self._save_config()
        return True


if __name__ == "__main__":
    # 测试代码
    import argparse

    parser = argparse.ArgumentParser(description='Get笔记配置管理')
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # add 命令
    add_parser = subparsers.add_parser('add', help='添加知识库')
    add_parser.add_argument('--name', required=True, help='知识库名称')
    add_parser.add_argument('--api-key', required=True, help='API Key')
    add_parser.add_argument('--topic-id', required=True, help='知识库ID')
    add_parser.add_argument('--default', action='store_true', help='设为默认')

    # list 命令
    list_parser = subparsers.add_parser('list', help='列出所有知识库')

    # show 命令
    show_parser = subparsers.add_parser('show', help='显示知识库配置')
    show_parser.add_argument('name', nargs='?', help='知识库名称（留空显示默认）')

    # default 命令
    default_parser = subparsers.add_parser('default', help='设置默认知识库')
    default_parser.add_argument('name', help='知识库名称')

    # set 命令
    set_parser = subparsers.add_parser('set', help='设置全局选项')
    set_parser.add_argument('key', help='选项名称（如 refs）')
    set_parser.add_argument('value', help='选项值（true/false）')

    # remove 命令
    remove_parser = subparsers.add_parser('remove', help='删除知识库')
    remove_parser.add_argument('name', help='知识库名称')

    args = parser.parse_args()

    manager = ConfigManager()

    if args.command == 'add':
        manager.add_knowledge_base(args.name, args.api_key, args.topic_id, args.default)
        print(f"✅ 已添加知识库: {args.name}")
        if args.default or manager.get_default() == args.name:
            print(f"✅ 设为默认知识库")

    elif args.command == 'list':
        bases = manager.list_knowledge_bases()
        default = manager.get_default()
        global_refs = manager.get_global_setting('refs', True)
        print("📚 已配置的知识库:\n")
        for name in bases:
            prefix = "⭐" if name == default else "  "
            print(f"{prefix} {name}")
        if not bases:
            print("  (无)")

        print(f"\n⚙️  全局设置:")
        print(f"   引用显示: {'开启' if global_refs else '关闭'}")

    elif args.command == 'show':
        config = manager.get_knowledge_base(args.name)
        if config:
            name = args.name or manager.get_default()
            print(f"📖 知识库: {name}")
            print(f"   API Key: {config['api_key'][:10]}...")
            print(f"   Topic ID: {config['topic_id']}")
        else:
            print("❌ 知识库不存在")

    elif args.command == 'default':
        if manager.set_default(args.name):
            print(f"✅ 默认知识库设为: {args.name}")
        else:
            print(f"❌ 知识库不存在: {args.name}")

    elif args.command == 'set':
        if args.key == 'refs':
            value = args.value.lower() == 'true'
            manager.set_global_setting('refs', value)
            print(f"✅ 全局引用显示已设置为: {'开启' if value else '关闭'}")
        else:
            print(f"❌ 未知的配置项: {args.key}")

    elif args.command == 'remove':
        if manager.remove_knowledge_base(args.name):
            print(f"✅ 已删除知识库: {args.name}")
        else:
            print(f"❌ 知识库不存在: {args.name}")

    else:
        parser.print_help()
