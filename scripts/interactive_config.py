#!/usr/bin/env python3
"""
交互式配置助手 - Get笔记知识库初始化
支持表格式输入多个知识库配置
"""

import sys
import json
from pathlib import Path
from config_manager import ConfigManager


class InteractiveConfigurator:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.kbs_to_add = []

    def print_header(self):
        """打印欢迎信息"""
        print("\n" + "="*70)
        print("🎯 Get笔记配置初始化助手")
        print("="*70)
        print("欢迎使用 Get笔记 Skill！让我们来配置您的知识库。\n")

    def print_table_header(self):
        """打印表格头"""
        print("\n" + "-"*70)
        print("知识库配置表 (表格模式)")
        print("-"*70)
        print(f"{'#':<3} {'库名':<20} {'API Key':<15} {'Topic ID':<12} {'描述':<12} {'默认':<3}")
        print("-"*70)

    def input_kb_count(self):
        """询问用户要添加多少个知识库"""
        while True:
            try:
                count = input("\n📝 您要配置多少个知识库？(输入数字，如 1, 2, 3): ").strip()
                if not count:
                    print("❌ 输入不能为空")
                    continue
                count = int(count)
                if count <= 0:
                    print("❌ 请输入大于 0 的数字")
                    continue
                if count > 10:
                    print("⚠️  建议最多添加 10 个知识库")
                    confirm = input("继续吗？(y/n): ").strip().lower()
                    if confirm != 'y':
                        continue
                return count
            except (ValueError, EOFError):
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                raise

    def input_kb_info(self, index):
        """统一表单输入知识库配置信息 - 一次性收集所有字段"""
        print(f"\n知识库 #{index} 配置表单")
        print("-" * 60)
        print("""
请按顺序输入以下信息（每个字段直接输入，回车确认）:

  1️⃣  知识库名称 (必填，不能重复)
  2️⃣  API Key (必填，来自 biji.com API 设置)
  3️⃣  Topic ID (必填，来自 biji.com API 设置)
  4️⃣  描述配置 (选项: auto 自动生成/skip 跳过/或输入自定义描述)
  5️⃣  默认库 (选项: y 是/n 否)
""")

        # 知识库名称
        while True:
            try:
                name = input("→ 知识库名称: ").strip()
            except EOFError:
                raise
            if not name:
                print("  ❌ 名称不能为空")
                continue
            if name in self.config_manager.config.get("knowledge_bases", {}):
                print(f"  ❌ 知识库 '{name}' 已存在")
                continue
            break

        # API Key
        while True:
            try:
                api_key = input("→ API Key: ").strip()
            except EOFError:
                raise
            if not api_key:
                print("  ❌ API Key 不能为空")
                continue
            if len(api_key) < 10:
                print("  ⚠️  API Key 看起来过短，输入 y 继续或重新输入: ", end="")
                try:
                    confirm = input().strip().lower()
                except EOFError:
                    raise
                if confirm == 'y':
                    break
                continue
            break

        # Topic ID
        while True:
            try:
                topic_id = input("→ Topic ID: ").strip()
            except EOFError:
                raise
            if not topic_id:
                print("  ❌ Topic ID 不能为空")
                continue
            break

        # 描述配置 (简化版)
        try:
            desc_input = input("→ 描述 (auto/skip/或自定义描述): ").strip().lower() or "auto"
        except EOFError:
            desc_input = "auto"

        if desc_input == "auto":
            description = "-auto"
        elif desc_input == "skip":
            description = ""
        else:
            description = desc_input

        # 是否为默认库
        default = False
        default_info = f"(当前默认库: {self.config_manager.config.get('default')})" if self.config_manager.config.get("default") else "(无默认库)"
        try:
            default_choice = input(f"→ 设为默认库？y/n {default_info}: ").strip().lower()
        except EOFError:
            default_choice = "n"

        default = (default_choice == 'y')

        print(f"\n✅ 已录入: {name} | {api_key[:10]}... | {topic_id} | 描述:{description} | 默认:{('是' if default else '否')}\n")

        return {
            "name": name,
            "api_key": api_key,
            "topic_id": topic_id,
            "description": description,
            "is_default": default
        }

    def collect_kb_configs(self):
        """收集所有知识库配置"""
        count = self.input_kb_count()

        print("\n" + "="*70)
        print(f"📋 请依次输入 {count} 个知识库的配置信息")
        print("="*70)

        for i in range(1, count + 1):
            kb_info = self.input_kb_info(i)
            self.kbs_to_add.append(kb_info)
            print(f"   ✅ 第 {i} 个知识库配置完成\n")

    def confirm_configs(self):
        """显示配置摘要供用户确认"""
        print("\n" + "="*70)
        print("📊 配置摘要")
        print("="*70)

        for i, kb in enumerate(self.kbs_to_add, 1):
            print(f"\n{i}. {kb['name']}")
            print(f"   API Key: {kb['api_key'][:10]}...{kb['api_key'][-5:]}")
            print(f"   Topic ID: {kb['topic_id']}")
            print(f"   描述: {kb['description'] if kb['description'] else '(无)'}")
            print(f"   默认库: {'是' if kb['is_default'] else '否'}")

        print("\n" + "-"*70)
        try:
            confirm = input("确认保存这些配置？(y/n): ").strip().lower()
        except EOFError:
            raise
        return confirm == 'y'

    def save_configs(self):
        """保存所有知识库配置"""
        print("\n💾 正在保存配置...")

        default_set = False
        for kb in self.kbs_to_add:
            if self.config_manager.add_knowledge_base(
                kb["name"],
                kb["api_key"],
                kb["topic_id"],
                kb.get("description", "")
            ):
                print(f"   ✅ 已保存: {kb['name']}")

                if kb["is_default"]:
                    self.config_manager.set_default(kb["name"])
                    default_set = True
            else:
                print(f"   ❌ 保存失败: {kb['name']}")

        print("\n✅ 知识库配置已保存！")
        return default_set

    def check_output_dir(self):
        """检查并配置输出目录"""
        output_dir = self.config_manager.get_output_dir()

        if output_dir:
            print(f"\n✅ 输出目录已配置: {output_dir}")
            return

        print("\n" + "="*70)
        print("📁 输出目录配置")
        print("="*70)
        print("生成的 Markdown 文档将保存在此目录。")
        print("默认情况下，文档将保存到当前工作目录。\n")

        try:
            configure = input("是否要设置输出目录？(y/n，建议选择): ").strip().lower()
        except EOFError:
            print("⏹️  输入已结束，跳过输出目录配置")
            return

        if configure == 'y':
            while True:
                try:
                    path = input("请输入输出目录路径 (支持 ~ 展开): ").strip()
                except EOFError:
                    print("⏹️  输入已结束，跳过输出目录配置")
                    return

                if not path:
                    print("❌ 路径不能为空")
                    continue

                if self.config_manager.set_output_dir(path):
                    print(f"✅ 输出目录已设置为: {self.config_manager.get_output_dir()}")
                    break
                else:
                    print("❌ 无法设置输出目录，请检查路径是否正确")
                    try:
                        retry = input("重试？(y/n): ").strip().lower()
                    except EOFError:
                        print("⏹️  输入已结束，跳过输出目录配置")
                        return
                    if retry != 'y':
                        break
        else:
            print("⏭️  跳过输出目录配置，可稍后使用以下命令设置:")
            print("   python3 scripts/biji.py config set-output <路径>")

    def run(self):
        """运行交互式配置流程"""
        self.print_header()

        # 检查是否已有配置
        existing_kbs = self.config_manager.config.get("knowledge_bases", {})
        if existing_kbs:
            print(f"ℹ️  已检测到 {len(existing_kbs)} 个已配置的知识库:")
            for name in existing_kbs:
                default_mark = " ⭐" if name == self.config_manager.config.get("default") else ""
                print(f"   - {name}{default_mark}")

            try:
                add_more = input("\n是否要添加更多知识库？(y/n): ").strip().lower()
            except EOFError:
                print("⏹️  输入已结束，取消配置")
                return

            if add_more != 'y':
                print("\n可使用以下命令管理知识库:")
                print("  - 查看配置: python3 scripts/biji.py config list")
                print("  - 添加知识库: python3 scripts/biji.py config add --name <名> --api-key <key> --topic-id <id>")
                print("  - 设置输出目录: python3 scripts/biji.py config set-output <路径>")
                return

        # 收集配置
        try:
            self.collect_kb_configs()
        except (EOFError, KeyboardInterrupt):
            raise

        # 确认配置
        try:
            if not self.confirm_configs():
                print("⏭️  已取消配置保存")
                return
        except EOFError:
            print("⏹️  输入已结束，取消配置保存")
            return

        # 保存配置
        self.save_configs()

        # 检查输出目录
        self.check_output_dir()

        # 完成
        print("\n" + "="*70)
        print("🎉 配置完成！")
        print("="*70)
        print("接下来您可以:")
        print("  1. 查看配置: python3 scripts/biji.py config list")
        print("  2. 搜索知识库: python3 scripts/biji.py search '您的问题'")
        print("  3. 管理输出: python3 scripts/biji.py config set-output <路径>")
        print("\n祝您使用愉快！✨\n")


def main():
    try:
        configurator = InteractiveConfigurator()
        configurator.run()
    except KeyboardInterrupt:
        print("\n\n⏹️  配置已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
