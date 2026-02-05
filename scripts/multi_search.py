#!/usr/bin/env python3
"""
Get笔记多库联合查询脚本
支持跨库检索和结果整合，用于复杂多步任务

使用方法:
    # 基本用法（JSON 格式）
    python3 multi_search.py '{"queries": ["查询1", "查询2"], "kbs": ["库A", "库B"]}'

    # 指定输出格式
    python3 multi_search.py '{"queries": ["查询"], "kbs": ["库A"]}' --format json

    # 创建 search_plan.md
    python3 multi_search.py '{"queries": ["查询"], "kbs": ["库A"]}' --plan
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from config_manager import ConfigManager
from biji import BijiClient


def create_search_plan(task_description, queries, kbs, output_dir=None):
    """
    创建物理任务规划文件 (Manus 模式)

    Args:
        task_description: 任务描述
        queries: 查询词列表
        kbs: 目标知识库列表
        output_dir: 输出目录

    Returns:
        Path: search_plan.md 文件路径
    """
    output_path = Path(output_dir) if output_dir else Path.cwd()
    plan_file = output_path / "search_plan.md"

    with open(plan_file, 'w', encoding='utf-8') as f:
        f.write(f"# 任务：{task_description}\n\n")
        f.write(f"- **状态**: 进行中\n")
        f.write(f"- **创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 检索目标\n\n")

        task_num = 1
        for kb in kbs:
            for query in queries:
                f.write(f"{task_num}. [ ] 在 [{kb}] 中搜索：{query}\n")
                task_num += 1

        f.write(f"\n{task_num}. [ ] 整合分析并输出报告\n\n")
        f.write("---\n\n")
        f.write("## 检索记录\n\n")
        f.write("（每次搜索后在此记录核心结论）\n\n")

    return plan_file


def update_search_plan(plan_file, kb_name, query, result_summary):
    """
    更新任务规划文件

    Args:
        plan_file: search_plan.md 文件路径
        kb_name: 知识库名称
        query: 查询词
        result_summary: 结果摘要
    """
    if not plan_file.exists():
        return

    with open(plan_file, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%H:%M:%S')
        f.write(f"### [{timestamp}] 来源: {kb_name} | 查询: {query}\n\n")
        f.write(f"{result_summary[:500]}{'...' if len(result_summary) > 500 else ''}\n\n")
        f.write("---\n\n")


def multi_search(task_json, create_plan=False, output_format='text', verbose=True):
    """
    执行多库联合查询

    Args:
        task_json: JSON 格式的任务配置
        create_plan: 是否创建 search_plan.md
        output_format: 输出格式 ('text' 或 'json')
        verbose: 是否输出详细信息

    Returns:
        dict: 查询结果
    """
    try:
        task_data = json.loads(task_json) if isinstance(task_json, str) else task_json
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {e}")
        return None

    queries = task_data.get('queries', [])
    target_kbs = task_data.get('kbs', [])
    task_desc = task_data.get('description', '多库联合查询')

    if not queries:
        print("❌ 错误: 未指定查询词 (queries)")
        return None

    config_mgr = ConfigManager()
    available_kbs = config_mgr.list_knowledge_bases()

    # 验证知识库
    if not target_kbs:
        # 未指定则使用所有库
        target_kbs = available_kbs
    else:
        # 验证指定的库是否存在
        invalid_kbs = [kb for kb in target_kbs if kb not in available_kbs]
        if invalid_kbs:
            print(f"❌ 错误: 以下知识库未配置: {', '.join(invalid_kbs)}")
            print(f"   可用的知识库: {', '.join(available_kbs)}")
            return None

    if verbose:
        print(f"🔍 多库联合查询")
        print(f"   查询词: {queries}")
        print(f"   目标库: {target_kbs}")
        print("=" * 60)

    # 创建物理规划文件
    plan_file = None
    if create_plan:
        plan_file = create_search_plan(task_desc, queries, target_kbs)
        if verbose:
            print(f"📋 已创建任务规划: {plan_file}")

    # 执行查询
    client = BijiClient()
    all_results = []
    total_tasks = len(target_kbs) * len(queries)
    current_task = 0

    for kb_name in target_kbs:
        for query in queries:
            current_task += 1
            if verbose:
                print(f"\n📚 [{current_task}/{total_tasks}] {kb_name}: {query}")
                print("-" * 40)

            # API 频率限制
            if current_task > 1:
                time.sleep(0.5)

            try:
                result = client.search(
                    query,
                    knowledge_base=kb_name,
                    new_session=True,
                    deep_seek=True,
                    refs=True
                )

                if result:
                    result_entry = {
                        "kb_name": kb_name,
                        "query": query,
                        "answer": result.get('answer', ''),
                        "refs": result.get('refs', []),
                        "success": True
                    }
                    all_results.append(result_entry)

                    # 更新规划文件
                    if plan_file:
                        summary = result.get('answer', '')[:300]
                        update_search_plan(plan_file, kb_name, query, summary)
                else:
                    all_results.append({
                        "kb_name": kb_name,
                        "query": query,
                        "answer": "",
                        "refs": [],
                        "success": False
                    })

            except Exception as e:
                if verbose:
                    print(f"❌ 查询失败: {e}")
                all_results.append({
                    "kb_name": kb_name,
                    "query": query,
                    "error": str(e),
                    "success": False
                })

    # 整合结果
    if verbose:
        print("\n" + "=" * 60)
        print(f"✅ 多库查询完成")
        print(f"   成功: {sum(1 for r in all_results if r.get('success'))}/{total_tasks}")

        if plan_file:
            print(f"   规划文件: {plan_file}")

    # 输出结果
    output = {
        "task": task_data,
        "results": all_results,
        "summary": {
            "total": total_tasks,
            "success": sum(1 for r in all_results if r.get('success')),
            "failed": sum(1 for r in all_results if not r.get('success'))
        }
    }

    if output_format == 'json':
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif output_format == 'markdown':
        print_markdown_report(output)

    return output


def print_markdown_report(output):
    """输出 Markdown 格式的报告"""
    print("\n# 多库检索报告\n")
    print(f"**查询词**: {output['task'].get('queries', [])}")
    print(f"**目标库**: {output['task'].get('kbs', [])}")
    print(f"**完成率**: {output['summary']['success']}/{output['summary']['total']}\n")
    print("---\n")

    for result in output['results']:
        if result.get('success'):
            print(f"## 来源: {result['kb_name']} | 查询: {result['query']}\n")
            print(f"{result['answer'][:500]}{'...' if len(result['answer']) > 500 else ''}\n")

            if result.get('refs'):
                print("### 引用")
                for i, ref in enumerate(result['refs'][:3], 1):
                    print(f"[{i}] {ref.get('title', '无标题')}")
            print("\n---\n")


def main():
    parser = argparse.ArgumentParser(
        description='Get笔记多库联合查询',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    # 基本用法
    python3 multi_search.py '{"queries": ["AI 趋势", "技术架构"], "kbs": ["政经参考", "技术笔记"]}'

    # 创建任务规划文件
    python3 multi_search.py '{"queries": ["查询"], "kbs": ["库A"]}' --plan

    # JSON 格式输出
    python3 multi_search.py '{"queries": ["查询"], "kbs": ["库A"]}' --format json

    # Markdown 报告
    python3 multi_search.py '{"queries": ["查询"], "kbs": ["库A"]}' --format markdown
        '''
    )

    parser.add_argument('task', help='JSON 格式的任务配置')
    parser.add_argument('--plan', action='store_true', help='创建 search_plan.md 任务规划')
    parser.add_argument('--format', choices=['text', 'json', 'markdown'], default='text',
                        help='输出格式（默认: text）')
    parser.add_argument('--quiet', action='store_true', help='静默模式')

    args = parser.parse_args()

    result = multi_search(
        args.task,
        create_plan=args.plan,
        output_format=args.format,
        verbose=not args.quiet
    )

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
