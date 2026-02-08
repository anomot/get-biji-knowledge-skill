#!/usr/bin/env python3
"""
Get笔记配置管理器
管理多个知识库的 API 凭证和元数据
支持知识库描述字段用于语义路由
"""

import json
import os
from pathlib import Path
from datetime import datetime

class ConfigManager:
    def __init__(self, config_file=None):
        if config_file is None:
            # 默认配置文件路径：~/.claude/get-biji-knowledge-skill-config.json
            # 放在 ~/.claude/ 目录下，避免被 rsync --delete 误删，且所有位置的 skill 都能访问
            home = Path.home()
            config_dir = home / ".claude"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / "get-biji-knowledge-skill-config.json"
            
            # 兼容旧配置文件名 (如果新文件不存在但旧文件存在，则重命名)
            old_config_file = config_dir / "get-biji-knowledge-config.json"
            if not self.config_file.exists() and old_config_file.exists():
                try:
                    old_config_file.rename(self.config_file)
                except Exception:
                    # 如果重命名失败，尝试读取旧文件内容并写入新文件
                    pass
        else:
            self.config_file = Path(config_file)

        self.config = self._load_config()
        self._migrate_config()  # 自动迁移旧配置

    def _load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"knowledge_bases": {}, "default": None, "global_settings": {"refs": True, "output_dir": None}}

    def _save_config(self):
        """保存配置文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def _migrate_config(self):
        """自动迁移旧配置格式，为缺失字段添加默认值"""
        migrated = False

        # 确保 global_settings 存在
        if "global_settings" not in self.config:
            self.config["global_settings"] = {"refs": True, "output_dir": None}
            migrated = True

        # 确保 global_settings 中有 output_dir 字段
        if "output_dir" not in self.config.get("global_settings", {}):
            self.config["global_settings"]["output_dir"] = None
            migrated = True

        # 为每个知识库添加缺失的字段
        for name, kb_config in self.config.get("knowledge_bases", {}).items():
            if "description" not in kb_config:
                kb_config["description"] = ""
                migrated = True
            if "last_updated" not in kb_config:
                kb_config["last_updated"] = ""
                migrated = True

        if migrated:
            self._save_config()

    def add_knowledge_base(self, name, api_key, topic_id, description="", set_default=False):
        """
        添加知识库配置

        Args:
            name: 知识库名称
            api_key: API Key
            topic_id: 知识库 ID
            description: 知识库描述（用于语义路由）
            set_default: 是否设为默认知识库
        """
        self.config["knowledge_bases"][name] = {
            "api_key": api_key,
            "topic_id": topic_id,
            "description": description,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if description else ""
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

    def get_all_kbs(self):
        """获取所有知识库的完整配置（包含 name）"""
        result = []
        for name, config in self.config.get("knowledge_bases", {}).items():
            kb_info = {"name": name}
            kb_info.update(config)
            result.append(kb_info)
        return result

    def get_all_descriptions(self):
        """
        获取所有知识库的名称和描述
        用于语义路由时的快速匹配

        Returns:
            list: [{"name": "库名", "description": "描述"}, ...]
        """
        result = []
        for name, config in self.config.get("knowledge_bases", {}).items():
            result.append({
                "name": name,
                "description": config.get("description", "")
            })
        return result

    def update_description(self, name, new_description):
        """
        更新知识库描述

        Args:
            name: 知识库名称
            new_description: 新的描述内容

        Returns:
            bool: 是否更新成功
        """
        if name in self.config["knowledge_bases"]:
            self.config["knowledge_bases"][name]["description"] = new_description
            self.config["knowledge_bases"][name]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_config()
            return True
        return False

    def get_kbs_by_descriptions(self, query, threshold=0.0):
        """
        根据查询语句匹配知识库描述（简单关键词匹配）

        Args:
            query: 用户查询语句
            threshold: 匹配阈值（0-1）

        Returns:
            list: 匹配的知识库列表，按相关度排序
        """
        results = []
        query_words = set(query.lower().split())

        for name, config in self.config.get("knowledge_bases", {}).items():
            description = config.get("description", "").lower()
            if not description:
                continue

            desc_words = set(description.split())
            # 计算简单的词汇重叠度
            overlap = len(query_words & desc_words)
            if query_words:
                score = overlap / len(query_words)
            else:
                score = 0

            if score > threshold:
                results.append({
                    "name": name,
                    "description": config.get("description", ""),
                    "score": score
                })

        # 按分数降序排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

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

    def get_default_kb(self):
        """获取默认知识库的完整配置"""
        default_name = self.config["default"]
        if default_name and default_name in self.config["knowledge_bases"]:
            kb_info = {"name": default_name}
            kb_info.update(self.config["knowledge_bases"][default_name])
            return kb_info
        return None

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

    def get_output_dir(self):
        """获取输出目录"""
        output_dir = self.get_global_setting('output_dir')
        if output_dir:
            return Path(output_dir)
        return None

    def set_output_dir(self, output_dir):
        """
        设置输出目录

        Args:
            output_dir: 输出目录路径

        Returns:
            bool: 是否设置成功
        """
        if output_dir:
            path = Path(output_dir).expanduser()
            # 验证路径有效性
            try:
                path.mkdir(parents=True, exist_ok=True)
                self.set_global_setting('output_dir', str(path))
                return True
            except Exception as e:
                print(f"❌ 无法创建输出目录: {e}")
                return False
        return False


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
    add_parser.add_argument('--description', default='', help='知识库描述（用于语义路由）')
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

    # update-desc 命令
    update_desc_parser = subparsers.add_parser('update-desc', help='更新知识库描述')
    update_desc_parser.add_argument('name', help='知识库名称')
    update_desc_parser.add_argument('description', help='新的描述内容')

    args = parser.parse_args()

    manager = ConfigManager()

    if args.command == 'add':
        manager.add_knowledge_base(args.name, args.api_key, args.topic_id, args.description, args.default)
        print(f"✅ 已添加知识库: {args.name}")
        if args.description:
            print(f"   描述: {args.description[:50]}{'...' if len(args.description) > 50 else ''}")
        if args.default or manager.get_default() == args.name:
            print(f"✅ 设为默认知识库")

    elif args.command == 'list':
        bases = manager.list_knowledge_bases()
        default = manager.get_default()
        global_refs = manager.get_global_setting('refs', True)
        print("📚 已配置的知识库:\n")
        for name in bases:
            prefix = "⭐" if name == default else "  "
            config = manager.get_knowledge_base(name)
            desc = config.get('description', '')
            desc_preview = f" - {desc[:30]}..." if desc else ""
            print(f"{prefix} {name}{desc_preview}")
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
            desc = config.get('description', '')
            if desc:
                print(f"   描述: {desc}")
            last_updated = config.get('last_updated', '')
            if last_updated:
                print(f"   更新时间: {last_updated}")
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

    elif args.command == 'update-desc':
        if manager.update_description(args.name, args.description):
            print(f"✅ 已更新知识库描述: {args.name}")
            print(f"   新描述: {args.description[:50]}{'...' if len(args.description) > 50 else ''}")
        else:
            print(f"❌ 知识库不存在: {args.name}")

    else:
        parser.print_help()
