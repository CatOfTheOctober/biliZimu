"""Prompt templates for the episode_draft LLM pipeline."""

from __future__ import annotations


ANGLE_TYPE_DOC = (
    "angle_type 只能从以下枚举中选择："
    "background、fact_update、host_judgment、mechanism_explanation、"
    "responsibility_focus、macro_extension、transition。"
)


def build_sentence_analysis_prompt() -> str:
    return (
        "你是中文时政视频整理助手。"
        "输入是一组按时间顺序排列的字幕句子。"
        "请把每句话标为 news_fact、host_commentary、transition、noise 之一，"
        "并给出 topic_hint、confidence、is_host_commentary。"
        "topic_hint 只需提炼本句最核心的讨论对象，不要扩展外部背景。"
        "confidence 范围为 0 到 1。"
        "必须返回 JSON 对象，格式为 {\"items\": [...]}。"
    )


def build_segment_extract_prompt() -> str:
    return (
        "你是中文新闻评论节目整理助手。"
        "任务是根据一个连续时间段的字幕，生成可供人工复核的结构化草稿。"
        "你只能依据输入字幕本身判断，不允许补充外部事实或背景。"
        "请输出 JSON 对象，字段必须包含："
        "topic_candidate、tracking_scope_candidate、segment_summary、retrieval_keywords、"
        "host_view_summary、quote_anchors、angle_type、segment_role、subscope_label、confidence。"
        "retrieval_keywords 是后续检索标签，不是展示口号。"
        "host_view_summary 必须是中性概括，不替主持人扩写。"
        "quote_anchors 必须引用输入里的原句，并且必须带 sentence_id。"
        f"{ANGLE_TYPE_DOC}"
        "segment_role 只能从以下枚举中选择：core_argument、supporting_context、proposal、transition。"
        "如果该段主要作用是举例、回忆、名言、类比、历史插段、传播背景或包装背景，应标为 supporting_context。"
        "如果该段主要提出结论、建议、替代方案或行动方向，应优先标为 proposal。"
        "不要把第一人称回忆、见闻、氛围描写自动提升为独立主题。"
        "subscope_label 可以是自由文本，但必须短、稳定、可复用。"
        "tracking_scope_candidate 必须明确后续跟踪边界，避免无限泛化。"
        "confidence 范围为 0 到 1。"
    )


def build_topic_merge_prompt() -> str:
    return (
        "你是中文新闻评论节目整理助手。"
        "任务是把多个 segment 归并为可跟踪的 news_topics。"
        "顶层主题必须严格聚焦，每期通常只保留 1 到 3 个真正可跟踪的主主题。"
        "你必须优先识别主主题，再把 supporting_context 片段挂到最相关的主主题下面，而不是新建 topic。"
        "如果多个 segment 讨论对象相同、后续跟踪边界相同，只是切入点不同，可以合并为一个主题。"
        "如果看似同类但后续跟踪对象不同，例如地方个案、责任主体、全国扩展，必须拆成不同主题。"
        "如果 segment_role 是 supporting_context，默认不能单独成为 topic，除非它本身包含脱离上下文仍可跟踪的公共对象。"
        "第一人称回忆、见闻、名言、类比、宣传片印象、氛围描写，默认属于 supporting_context。"
        "最终输出的主视图是主题视图，不是纯时间视图。"
        "每个 topic 必须包含 canonical_topic、tracking_scope、retrieval_keywords、"
        "host_overall_view_summary、segment_ids、review_status、confidence。"
        "canonical_topic 应该稳定、可复用，优先选择后续跟踪能持续使用的主题名。"
        "retrieval_keywords 仍然服务检索，不是视频画面文案。"
        "host_overall_view_summary 必须综合该主题下多个时间段的主持人核心判断。"
        "必须返回 JSON 对象，格式为 {\"topics\": [...]}。"
    )
