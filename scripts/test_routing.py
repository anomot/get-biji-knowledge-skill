#!/usr/bin/env python3
"""
语义路由测试脚本
验证不同描述下 AI 的分发准确率

使用方法:
    python3 test_routing.py
"""

import sys
from pathlib import Path

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from config_manager import ConfigManager


def test_routing_logic():
    """测试语义路由逻辑"""
    print("=" * 60)
    print("📊 语义路由测试")
    print("=" * 60)

    # 测试用知识库配置
    test_kbs = [
        {"name": "政经参考", "description": "涵盖 2026 房地产 政策 宏观经济 法律法规 政府报告"},
        {"name": "技术笔记", "description": "Python 开发 提示词工程 AI 代理 架构 LLM 编程"},
        {"name": "投资参考", "description": "股票 房地产 行业分析 投资建议 财务报表 基金"},
        {"name": "学习笔记", "description": "读书笔记 个人成长 时间管理 效率工具"}
    ]

    # 测试查询
    test_queries = [
        ("分析 2026 房地产政策", ["政经参考", "投资参考"]),
        ("如何构建 AI 代理？", ["技术笔记"]),
        ("房地产行业投资建议和政策汇总", ["政经参考", "投资参考"]),
        ("Python 最佳实践", ["技术笔记"]),
        ("股票投资策略", ["投资参考"]),
        ("如何提高学习效率", ["学习笔记"]),
        ("LLM 提示词工程技巧", ["技术笔记"]),
        ("宏观经济分析报告", ["政经参考"]),
    ]

    print("\n📚 测试知识库配置:\n")
    for kb in test_kbs:
        print(f"  - {kb['name']}: {kb['description'][:50]}...")

    print("\n" + "-" * 60)
    print("\n🔍 开始测试查询路由:\n")

    correct = 0
    total = len(test_queries)

    for query, expected_kbs in test_queries:
        result = simulate_routing(query, test_kbs)
        matched_kbs = [r['name'] for r in result[:2]]  # 取前2个匹配

        # 检查是否有预期的库在结果中
        hit = any(kb in matched_kbs for kb in expected_kbs)
        status = "✅" if hit else "❌"

        if hit:
            correct += 1

        print(f"{status} 查询: {query}")
        print(f"   预期: {expected_kbs}")
        print(f"   实际: {matched_kbs}")
        if result:
            print(f"   分数: {[f'{r[\"name\"]}({r[\"score\"]:.2f})' for r in result[:3]]}")
        print()

    print("-" * 60)
    print(f"\n📈 测试结果: {correct}/{total} ({correct/total*100:.1f}% 准确率)")

    if correct / total < 0.8:
        print("\n⚠️ 建议: 准确率较低，请检查知识库描述是否包含足够的关键词")
    else:
        print("\n✅ 语义路由表现良好")

    return correct / total


def simulate_routing(query, kb_list):
    """
    模拟语义路由逻辑（简单关键词匹配）

    Args:
        query: 用户查询语句
        kb_list: 知识库配置列表

    Returns:
        list: 匹配结果，按分数降序排列
    """
    query_words = set(query.lower().split())
    results = []

    for kb in kb_list:
        description = kb.get('description', '').lower()
        if not description:
            continue

        desc_words = set(description.split())
        # 计算词汇重叠度
        overlap = len(query_words & desc_words)
        if query_words:
            score = overlap / len(query_words)
        else:
            score = 0

        results.append({
            'name': kb['name'],
            'description': kb['description'],
            'score': score
        })

    # 按分数降序排序
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def test_with_real_config():
    """使用真实配置测试"""
    print("\n" + "=" * 60)
    print("📋 使用真实配置测试")
    print("=" * 60)

    config_mgr = ConfigManager()
    kb_names = config_mgr.list_knowledge_bases()

    if not kb_names:
        print("\n❌ 未配置任何知识库")
        print("   请先使用 'biji.py config add' 添加知识库")
        return

    print(f"\n📚 已配置的知识库: {len(kb_names)} 个\n")

    for name in kb_names:
        config = config_mgr.get_knowledge_base(name)
        desc = config.get('description', '')
        has_desc = "✅" if desc else "⚠️ 无描述"
        print(f"  {has_desc} {name}")
        if desc:
            print(f"      描述: {desc[:60]}...")

    # 检查描述覆盖率
    kbs_with_desc = sum(1 for name in kb_names
                       if config_mgr.get_knowledge_base(name).get('description'))
    coverage = kbs_with_desc / len(kb_names) if kb_names else 0

    print(f"\n📊 描述覆盖率: {kbs_with_desc}/{len(kb_names)} ({coverage*100:.1f}%)")

    if coverage < 0.5:
        print("\n💡 建议: 为知识库添加描述以启用语义路由功能")
        print("   使用: python3 biji.py config update-desc '库名' '描述内容'")
        print("   或者: python3 sync_metadata.py --kb '库名' 自动生成描述")


def main():
    print("🧪 Get笔记语义路由测试工具\n")

    # 运行模拟测试
    accuracy = test_routing_logic()

    # 检查真实配置
    test_with_real_config()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
