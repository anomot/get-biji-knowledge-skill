#!/usr/bin/env python3
"""
Get笔记知识库元数据同步脚本
自动生成和更新知识库描述，用于语义路由

使用方法:
    # 使用 search API 生成描述（推荐）
    python3 sync_metadata.py --kb "知识库名称"

    # 使用 recall API 生成描述（备用）
    python3 sync_metadata.py --kb "知识库名称" --use-recall

    # 仅测试不更新
    python3 sync_metadata.py --kb "知识库名称" --dry-run

    # 批量更新所有知识库
    python3 sync_metadata.py --all
"""

import argparse
import sys
import json
import re
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config_manager import ConfigManager
from recall_knowledge import recall_knowledge
from search_knowledge import search_knowledge

# 方法1：使用 search API 的元查询（推荐）
# 多角度查询模板，用于获取全面的知识库画像
META_QUERIES = [
    # 查询1: 核心主题和关键词
    """这个知识库主要涵盖哪些核心主题和领域？请列出最重要的5-8个关键词标签。""",

    # 查询2: 内容类型和特点
    """这个知识库的内容类型有哪些特点？主要记录了什么样的内容？""",

    # 查询3: 适用场景和应用
    """这个知识库适用于什么场景？可以解决什么问题或支持什么决策？"""
]

# 单次查询模板（向后兼容）
META_QUERY = """请用150字以内总结这个知识库：
1. 核心主题和领域（用关键词标签形式）
2. 主要内容类型
3. 适用场景

格式：该库主要涵盖 [领域]，核心关键词包括 [标签1、标签2、标签3...]，重点关注 [内容特点]，适用于 [场景]。"""

# 方法2：使用 recall API 的提示词模板（备用）
DESCRIPTION_PROMPT = """
你是一名专业的知识索引架构师，擅长从非结构化笔记中提取核心知识图谱。
请阅读以下从用户的 Get 笔记知识库中召回的笔记摘要，并生成该知识库的"领域描述（Description）"。

# Constraints
1. 客观性：仅根据提供的素材描述领域，不进行主观臆断。
2. 全面性：覆盖笔记中出现的主要学科、行业或主题，并标注核心关键词标签。
3. 简练性：总长度控制在 150 字以内，包含至少5个关键词标签。
4. 格式：采用"核心领域 + 关键词标签 + 重点关注 + 适用场景"的结构。

# Output Template
该库主要涵盖 [核心领域]，核心关键词包括 [标签1、标签2、标签3、标签4、标签5]，重点记录了 [内容特点]，适用于 [场景 X] 或 [决策 Y]。
"""


def get_kb_summary(api_key, topic_id, sample_query="最近更新的内容摘要", top_k=10):
    """
    通过 recall API 获取知识库内容摘要

    Args:
        api_key: API Key
        topic_id: 知识库 ID
        sample_query: 用于召回的查询词
        top_k: 返回结果数量

    Returns:
        str: 召回内容的摘要文本
    """
    # 静默召回，不打印详细信息
    import io
    from contextlib import redirect_stdout

    # 捕获标准输出
    f = io.StringIO()
    with redirect_stdout(f):
        result = recall_knowledge(
            api_key=api_key,
            topic_id=topic_id,
            question=sample_query,
            top_k=top_k,
            intent_rewrite=True,
            select_matrix=True
        )

    if not result:
        return None

    # 构建摘要文本
    summaries = []
    for item in result:
        title = item.get('title', '无标题')
        content = item.get('content', '')[:300]  # 取前300字符
        item_type = item.get('type', 'unknown')
        summaries.append(f"[{item_type}] {title}: {content}")

    return "\n\n".join(summaries)


def generate_description_prompt(kb_name, raw_materials, existing_desc=""):
    """
    生成用于 LLM 的描述生成提示词

    Args:
        kb_name: 知识库名称
        raw_materials: 召回的原始素材
        existing_desc: 现有描述（用于增量更新）

    Returns:
        str: 完整的提示词
    """
    prompt = DESCRIPTION_PROMPT + f"\n\n# Inputs\n知识库名称: {kb_name}\n\n笔记素材:\n{raw_materials}"

    if existing_desc:
        prompt += f"\n\n原有描述（请进行去重整合）:\n{existing_desc}"

    return prompt


def get_description_via_search(api_key, topic_id, kb_name, query_rounds=3, verbose=True):
    """
    通过 search API 直接获取知识库描述（推荐方法）
    使用多轮查询 + 深度思考模式获取更全面的知识库画像

    Args:
        api_key: API Key
        topic_id: 知识库 ID
        kb_name: 知识库名称
        query_rounds: 查询轮数（1-3），默认3轮
        verbose: 是否输出详细信息

    Returns:
        str: 生成的描述，失败返回 None
    """
    if verbose:
        if query_rounds > 1:
            print(f"\n📡 使用 search API 生成描述 (深度思考 + {query_rounds}轮查询)...")
        else:
            print(f"\n📡 使用 search API 生成描述 (深度思考模式)...")

    try:
        # 根据查询轮数选择策略
        if query_rounds == 1:
            # 单次查询
            queries = [META_QUERY]
        else:
            # 多轮查询：使用不同角度的问题
            queries = META_QUERIES[:min(query_rounds, len(META_QUERIES))]

        all_results = []

        for i, query in enumerate(queries, 1):
            if verbose and len(queries) > 1:
                print(f"   🔍 第 {i}/{len(queries)} 轮查询...")

            # 第一轮查询必须使用新会话（不携带历史信息）
            # 第2-3轮也使用独立新会话，避免 API 返回空结果或排除前轮内容
            # 注意：携带 history 会让 API 认为是追问，可能导致空结果或遗漏内容
            # 使用流式 API (stream=True) 与 biji.py 保持一致
            result = search_knowledge(
                api_key=api_key,
                topic_id=topic_id,
                question=query,
                deep_seek=True,      # 启用深度思考模式
                refs=False,
                history=[],          # 使用空列表表示新会话（与 biji.py 一致）
                stream=True,         # 使用流式 API
                verbose=False,       # 静默模式，不打印详细信息
                debug=False,         # 关闭调试模式
                max_retries=1        # 遇到频率限制时自动重试1次
            )

            if not result:
                if verbose:
                    print(f"      ⚠️ 第 {i} 轮返回空结果")
                continue

            # 提取内容字段（支持流式和非流式两种响应格式）
            content = None
            if isinstance(result, dict):
                # 流式 API 返回格式: {"answer": "...", "refs": [...]}
                if 'answer' in result:
                    content = result['answer']
                # 非流式 API 返回格式: {"answers": "...", "deep_seek": "..."}
                elif 'answers' in result:
                    content = result['answers']
                elif 'content' in result:
                    content = result['content']
            elif isinstance(result, str):
                content = result

            if content and len(content) >= 20:
                all_results.append(content)
                if verbose and len(queries) > 1:
                    # 显示简短预览
                    preview = content[:80].replace('\n', ' ')
                    print(f"      ✓ 已获取 ({len(content)} 字符): {preview}...")

        if not all_results:
            if verbose:
                print(f"   ❌ 所有查询均失败")
            return None

        # 整合多轮结果
        if len(all_results) == 1:
            # 单次查询，直接提取
            description = extract_description_from_response(all_results[0])
        else:
            # 多轮查询，整合结果
            if verbose:
                print(f"   🔄 整合 {len(all_results)} 轮查询结果...")
            description = integrate_multi_round_results(all_results, kb_name)

        if verbose:
            print(f"   ✅ 生成的描述: {description[:100]}...")

        return description

    except Exception as e:
        if verbose:
            print(f"   ❌ search API 失败: {str(e)}")
            import traceback
            traceback.print_exc()
        return None


def extract_description_from_response(content):
    """
    从 API 响应中提取结构化描述

    Args:
        content: API 返回的完整内容

    Returns:
        str: 提取的描述（150字以内）
    """
    # 保留原始内容用于标签提取
    original_content = content

    # 清理 markdown 标记
    clean_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
    clean_content = re.sub(r'[*_`]+', '', clean_content)
    clean_content = clean_content.strip()

    # 方法1：查找"该库主要涵盖"格式的句子
    pattern = r'该库主要涵盖[^。]+。'
    matches = re.findall(pattern, clean_content)
    if matches:
        desc = matches[0]
        if len(desc) > 180:
            desc = desc[:177] + '...'
        return desc

    # 方法2：查找标签总结行（如 "#标签1 #标签2 #标签3"）
    tag_line_pattern = r'#([^\s#，。、！？\n]+)'
    tag_matches = re.findall(tag_line_pattern, original_content)
    if tag_matches and len(tag_matches) >= 3:
        # 找到了标签行，提取标签
        keywords = tag_matches[:8]  # 最多8个
        # 尝试提取主题描述
        theme_patterns = [
            r'核心主题[：:涵盖]*([^，。\n]{5,40})',
            r'主要涵盖([^，。\n]{5,40})',
            r'聚焦于([^，。\n]{5,40})',
        ]
        theme_text = None
        for pattern in theme_patterns:
            matches = re.findall(pattern, clean_content)
            if matches:
                theme_text = matches[0].strip()
                break

        if not theme_text and keywords:
            theme_text = '、'.join(keywords[:3])

        # 组装描述
        keywords_text = '、'.join(keywords)
        if theme_text:
            description = f"该库主要涵盖{theme_text}，核心关键词包括{keywords_text}。"
        else:
            description = f"核心关键词包括{keywords_text}。"

        if len(description) > 180:
            keywords_text = '、'.join(keywords[:5])
            description = f"该库主要涵盖{theme_text}，核心关键词包括{keywords_text}。" if theme_text else f"核心关键词包括{keywords_text}。"

        if len(description) > 180:
            description = description[:177] + '...'

        return description

    # 方法3：查找关键词标签段落
    lines = clean_content.split('\n')
    desc_parts = []
    for line in lines:
        line = line.strip()
        if any(keyword in line for keyword in ['核心主题', '关键领域', '关键词', '适用于']):
            clean_line = re.sub(r'[#*`\-]', '', line).strip()
            if clean_line and len(clean_line) > 10:
                desc_parts.append(clean_line)

    if desc_parts:
        combined = '，'.join(desc_parts[:3])
        if len(combined) > 180:
            combined = combined[:177] + '...'
        return f"该库主要涵盖{combined}"

    # 方法4：简单截取前180字
    clean_content = re.sub(r'[#*`\-\n]+', ' ', content).strip()
    if len(clean_content) > 180:
        return clean_content[:177] + '...'
    return clean_content


def integrate_multi_round_results(results, kb_name):
    """
    整合多轮查询结果，生成综合描述
    优先提取标签格式的关键词，过滤泛化词汇

    Args:
        results: 多轮查询的结果列表
        kb_name: 知识库名称

    Returns:
        str: 整合后的描述（150字以内）
    """
    from collections import Counter

    # 扩展的停用词表（过滤泛化词汇）
    stop_words = {
        '这个', '知识', '知识库', '主要', '包括', '涵盖', '内容', '可以', '进行',
        '相关', '不同', '各种', '通过', '以及', '政策', '框架', '机会', '关键',
        '支撑', '领域', '方面', '问题', '分析', '发展', '建议', '重点', '核心',
        '提供', '具有', '需要', '关注', '强调', '特点', '价值', '作用', '影响'
    }

    # 分类提取关键词
    tag_keywords = []      # 标签格式的关键词（最高优先级）
    long_keywords = []     # 4-6字的专业术语（高优先级）
    medium_keywords = []   # 3字词（中优先级）
    themes = []            # 主题描述
    scenarios = []         # 适用场景

    for content in results:
        # 保留原始内容用于标签提取
        original_content = content

        # 清理markdown用于普通提取
        clean_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        clean_content = re.sub(r'[*_`]+', '', clean_content)

        # 1. 优先提取标签格式的关键词（#标签）
        tag_pattern = r'#([^\s#，。、！？\n]{2,10})'
        tags = re.findall(tag_pattern, original_content)
        # 过滤停用词和泛化词
        tags = [t for t in tags if t not in stop_words and len(t) >= 3]
        tag_keywords.extend(tags)

        # 2. 提取「」格式的关键词
        bracket_pattern = r'「([^」]{2,10})」'
        bracket_tags = re.findall(bracket_pattern, clean_content)
        bracket_tags = [t for t in bracket_tags if t not in stop_words and len(t) >= 3]
        tag_keywords.extend(bracket_tags)

        # 3. 提取中文词汇（2-8字）
        words = re.findall(r'[\u4e00-\u9fa5]{2,8}', clean_content)

        # 按长度分类
        for word in words:
            if word in stop_words:
                continue
            if 4 <= len(word) <= 8:
                long_keywords.append(word)
            elif len(word) == 3:
                medium_keywords.append(word)

        # 4. 提取主题描述（从第1轮和第2轮）
        theme_patterns = [
            r'核心主题聚焦于([^，。]{5,40})',
            r'主要涵盖([^，。]{5,40})',
            r'核心主题[：:]([^，。]{5,40})',
            r'关键领域[：:]([^，。]{5,40})',
        ]
        for pattern in theme_patterns:
            matches = re.findall(pattern, clean_content)
            for m in matches:
                m = m.strip()
                if len(m) >= 5 and m not in stop_words:
                    themes.append(m)

        # 5. 提取适用场景（从第3轮）
        scenario_patterns = [
            r'适用于([^，。]{5,30})',
            r'为([^，。]{5,30})提供',
            r'服务于([^，。]{5,30})',
        ]
        for pattern in scenario_patterns:
            matches = re.findall(pattern, clean_content)
            for m in matches:
                m = m.strip()
                if len(m) >= 5 and not any(sw in m for sw in stop_words):
                    scenarios.append(m)

    # 统计词频并去重
    tag_counter = Counter(tag_keywords)
    long_counter = Counter(long_keywords)
    medium_counter = Counter(medium_keywords)

    # 按优先级组装关键词列表
    final_keywords = []

    # 1. 优先：标签格式的关键词（取前5个）
    for word, count in tag_counter.most_common(8):
        if word not in final_keywords:
            final_keywords.append(word)

    # 2. 其次：4-8字的长关键词（至少出现2次，取前3个）
    for word, count in long_counter.most_common(10):
        if count >= 2 and word not in final_keywords and len(final_keywords) < 8:
            final_keywords.append(word)

    # 3. 补充：3字关键词（至少出现3次，取前2个）
    for word, count in medium_counter.most_common(10):
        if count >= 3 and word not in final_keywords and len(final_keywords) < 8:
            final_keywords.append(word)

    # 限制最终数量
    final_keywords = final_keywords[:8]

    # 去重主题和场景
    themes = list(dict.fromkeys(themes))[:2]  # 保持顺序的去重
    scenarios = list(dict.fromkeys(scenarios))[:2]

    # 组装描述
    # 主题部分
    if themes and len(themes[0]) < 30:
        theme_text = themes[0]
    elif final_keywords:
        # 使用前3个关键词作为主题
        theme_text = '、'.join(final_keywords[:3])
    else:
        theme_text = "综合知识"

    # 关键词部分
    if final_keywords:
        keywords_text = '、'.join(final_keywords)
    else:
        keywords_text = "多领域知识"

    # 场景部分
    if scenarios and len(scenarios[0]) < 25:
        scenario_text = scenarios[0]
    else:
        scenario_text = "政策研究与决策参考"

    # 生成最终描述
    description = f"该库主要涵盖{theme_text}，核心关键词包括{keywords_text}，适用于{scenario_text}。"

    # 长度控制
    if len(description) > 180:
        # 如果太长，缩减关键词数量
        keywords_text_short = '、'.join(final_keywords[:5])
        description = f"该库主要涵盖{theme_text}，核心关键词包括{keywords_text_short}，适用于{scenario_text}。"

    if len(description) > 180:
        # 还是太长，进一步缩减
        keywords_text_short = '、'.join(final_keywords[:4])
        description = f"该库主要涵盖{theme_text}，核心关键词包括{keywords_text_short}，适用于{scenario_text}。"

    if len(description) > 180:
        description = description[:177] + '...'

    return description


def sync_single_kb(manager, kb_name, use_recall=False, query_rounds=3, dry_run=False, verbose=True):
    """
    同步单个知识库的描述

    Args:
        manager: ConfigManager 实例
        kb_name: 知识库名称
        use_recall: 是否使用 recall API（默认使用 search API）
        query_rounds: 查询轮数（1-3），默认3轮
        dry_run: 是否仅测试不更新
        verbose: 是否输出详细信息

    Returns:
        dict: {"success": bool, "description": str, "method": str}
    """
    kb_config = manager.get_knowledge_base(kb_name)
    if not kb_config:
        if verbose:
            print(f"❌ 知识库不存在: {kb_name}")
        return {"success": False, "description": None, "method": None}

    api_key = kb_config['api_key']
    topic_id = kb_config['topic_id']
    existing_desc = kb_config.get('description', '')

    if verbose:
        print(f"\n🔍 正在分析知识库: [{kb_name}]...")
        print(f"   Topic ID: {topic_id}")
        if existing_desc:
            print(f"   现有描述: {existing_desc[:50]}...")

    description = None

    # 方法1：使用 search API（推荐）
    if not use_recall:
        description = get_description_via_search(api_key, topic_id, kb_name, query_rounds, verbose)

        if description and not dry_run:
            # 直接更新配置
            if manager.update_description(kb_name, description):
                if verbose:
                    print(f"\n✅ 已更新知识库描述")
                    print(f"   描述: {description}")
                return {"success": True, "description": description, "method": "search"}
            else:
                if verbose:
                    print(f"\n❌ 更新配置失败")
                return {"success": False, "description": description, "method": "search"}

        if dry_run and description:
            if verbose:
                print(f"\n📝 [Dry Run] 生成的描述:")
                print(f"   {description}")
                print(f"\n💡 下一步: 移除 --dry-run 参数以保存描述")
            return {"success": True, "description": description, "method": "search"}

    # 方法2：使用 recall API（备用）
    if use_recall or (not description and use_recall):
        if verbose:
            print(f"\n📡 使用 recall API 生成描述 (备用方法)...")

        raw_materials = get_kb_summary(api_key, topic_id)

        if not raw_materials:
            if verbose:
                print(f"❌ 无法获取知识库内容，请检查 API 配置")
            return {"success": False, "description": None, "method": "recall"}

        if verbose:
            print(f"   ✅ 已召回 {len(raw_materials.split(chr(10) + chr(10)))} 条内容")

        # 生成提示词
        prompt = generate_description_prompt(kb_name, raw_materials, existing_desc)

        if dry_run:
            if verbose:
                print(f"\n📝 [Dry Run] 需要手动生成描述:")
                print("-" * 50)
                print(f"素材摘要（共 {len(raw_materials)} 字符）:\n")
                print(raw_materials[:2000] + "..." if len(raw_materials) > 2000 else raw_materials)
                print("-" * 50)
                print(f"\n💡 提示: 请生成一段 150 字以内的描述，包含至少5个关键词标签")
                print(f"   格式: 该库主要涵盖 [核心领域]，核心关键词包括 [标签1、标签2...]，重点记录了 [内容特点]，适用于 [场景]。")
            return {"success": True, "description": None, "method": "recall"}

        # 输出提示词，让用户/Claude 生成描述
        if verbose:
            print(f"\n📝 请根据以下素材为知识库 [{kb_name}] 生成描述:")
            print("-" * 50)
            print(f"素材摘要（共 {len(raw_materials)} 字符）:\n")
            print(raw_materials[:2000] + "..." if len(raw_materials) > 2000 else raw_materials)
            print("-" * 50)
            print(f"\n💡 提示: 请生成一段 150 字以内的描述，包含至少5个关键词标签")
            print(f"   格式: 该库主要涵盖 [核心领域]，核心关键词包括 [标签1、标签2...]，适用于 [场景]。")
            print(f"\n📌 生成后，请使用以下命令更新:")
            print(f'   python3 scripts/config_manager.py update-desc "{kb_name}" "您的描述内容"')

        return {"success": True, "description": None, "method": "recall"}

    # 如果两种方法都失败
    if verbose:
        print(f"\n❌ 无法生成描述")
    return {"success": False, "description": None, "method": None}


def sync_all_kbs(manager, use_recall=False, query_rounds=3, dry_run=False, verbose=True):
    """
    同步所有知识库的描述

    Args:
        manager: ConfigManager 实例
        use_recall: 是否使用 recall API
        query_rounds: 查询轮数（1-3），默认3轮
        dry_run: 是否仅测试不更新
        verbose: 是否输出详细信息

    Returns:
        list: 每个知识库的同步结果
    """
    kb_names = manager.list_knowledge_bases()

    if not kb_names:
        if verbose:
            print("❌ 未配置任何知识库")
        return []

    results = []
    for kb_name in kb_names:
        result = sync_single_kb(manager, kb_name, use_recall, query_rounds, dry_run, verbose)
        result["kb_name"] = kb_name
        results.append(result)

        if verbose:
            print("\n" + "=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Get笔记知识库元数据同步 - 自动生成描述',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    # 使用 search API 生成描述（默认3轮查询 + 深度思考）
    python3 sync_metadata.py --kb "技术笔记"

    # 指定查询轮数（1-3轮）
    python3 sync_metadata.py --kb "技术笔记" --rounds 1

    # 使用 recall API 生成描述（备用）
    python3 sync_metadata.py --kb "技术笔记" --use-recall

    # 验证效果但不保存
    python3 sync_metadata.py --kb "技术笔记" --dry-run

    # 批量更新所有知识库
    python3 sync_metadata.py --all

    # 静默模式（仅输出 JSON）
    python3 sync_metadata.py --kb "技术笔记" --quiet
        '''
    )

    parser.add_argument('--kb', type=str, help='指定知识库名称')
    parser.add_argument('--all', action='store_true', help='更新所有知识库')
    parser.add_argument('--rounds', type=int, default=3, choices=[1, 2, 3],
                        help='查询轮数（1-3），默认3轮。多轮查询可获得更全面的描述')
    parser.add_argument('--use-recall', action='store_true', help='使用 recall API（备用方法，默认使用 search API）')
    parser.add_argument('--dry-run', action='store_true', help='仅测试生成效果，不保存')
    parser.add_argument('--quiet', action='store_true', help='静默模式，仅输出 JSON')

    args = parser.parse_args()

    manager = ConfigManager()
    verbose = not args.quiet

    if args.kb:
        # 同步单个知识库
        result = sync_single_kb(manager, args.kb, args.use_recall, args.rounds, args.dry_run, verbose)
        if args.quiet:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result.get("success") and result.get("method") == "search" and not args.dry_run:
            print(f"\n✅ 同步完成 (使用 search API，{args.rounds} 轮查询 + 深度思考)")
        elif result.get("success") and result.get("method") == "recall":
            print(f"\n💡 下一步: 根据输出的素材手动生成描述，然后使用 config_manager.py update-desc 更新")
    elif args.all:
        # 同步所有知识库
        results = sync_all_kbs(manager, args.use_recall, args.rounds, args.dry_run, verbose)
        if args.quiet:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            success_count = sum(1 for r in results if r.get("success"))
            print(f"\n✅ 同步完成: {success_count}/{len(results)} 个知识库 ({args.rounds} 轮查询 + 深度思考)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
