"""
gate.py — skill-optimizer 的 gate prompt 文本生成器。

纯文本工具：为 gate-agent 生成裁判 prompt。
不调用任何 LLM。不写文件。
零外部依赖（仅 Python 3 标准库）。

用法:
    from gate import build_gate_prompt

    prompt = build_gate_prompt(
        new_skill="...完整 SKILL.md 内容...",
        clusters=[
            {
                "cluster_id": "c_001",
                "root_cause": "命名检查范围过大",
                "type": "corrected",
                "correction": "项目有 lint 管命名，不需要检查",
                "friction_detail": None,
                "count": 2
            }
        ],
        mode="text_edit"
    )
    # prompt 为字符串，直接发给 gate-agent
"""


def _format_cluster_text_edit(cluster):
    """MODE 1（文本编辑）gate prompt 的单个 cluster 格式化。"""
    label = cluster["type"].upper()
    count = cluster.get("count", 1)
    root_cause = cluster["root_cause"]
    correction = cluster.get("correction") or cluster.get("friction_detail", "")
    return (
        f"- Cluster {cluster['cluster_id']} ({label} x{count}): {root_cause}.\n"
        f"  指导: \"{correction}\""
    )


def _format_cluster_rewrite(cluster):
    """MODE 2（全量重写）gate prompt 的单个 cluster 格式化。"""
    label = cluster["type"].upper()
    count = cluster.get("count", 1)
    root_cause = cluster["root_cause"]
    correction = cluster.get("correction") or cluster.get("friction_detail", "")
    return (
        f"- Cluster {cluster['cluster_id']} ({label} x{count}): {root_cause}.\n"
        f"  用户纠正: \"{correction}\""
    )


def build_gate_prompt(new_skill, clusters, mode="text_edit"):
    """
    生成 gate 裁判 prompt。

    参数:
        new_skill (str): 候选 skill 内容（应用 edits 后或全量重写后）。
        clusters (list[dict]): 待验证的信号 cluster。每个 cluster 需包含:
            - cluster_id (str)
            - root_cause (str): 根因描述
            - type (str): "corrected" 或 "friction"
            - correction (str|None): 用户纠正内容
            - friction_detail (str|None): 摩擦详情
            - count (int, 可选): cluster 包含的信号数
        mode (str): "text_edit"（MODE 1，默认）或 "rewrite"（MODE 2）。

    返回:
        str: 裁判 prompt 文本。
    """
    if mode == "rewrite":
        return _build_rewrite_prompt(new_skill, clusters)
    return _build_text_edit_prompt(new_skill, clusters)


def _build_text_edit_prompt(new_skill, clusters):
    """MODE 1: 文本编辑 gate — 每个 cluster YES/NO 判定。"""

    cluster_entries = "\n".join(_format_cluster_text_edit(c) for c in clusters)

    prompt = (
        "Judge the following skill change against historical signals:\n\n"
        "**New Skill:**\n"
        f"{new_skill}\n\n"
        "**Signals to verify:**\n"
        f"{cluster_entries}\n\n"
        "For each cluster: If agent had the new skill above, "
        "would this signal still have occurred? "
        "Reply with JSON:\n"
        '[{"cluster_id": "...", "verdict": "YES"|"NO", "reason": "..."}, ...]\n'
    )
    return prompt


def _build_rewrite_prompt(new_skill, clusters):
    """MODE 2: 全量重写 gate — 每个 cluster COVERED/NOT_COVERED 判定。"""

    cluster_entries = "\n".join(_format_cluster_rewrite(c) for c in clusters)

    prompt = (
        "Judge the rewritten skill against historical signals:\n\n"
        "**Rewritten Skill:**\n"
        f"{new_skill}\n\n"
        "**Signals to verify:**\n"
        f"{cluster_entries}\n\n"
        "For each cluster: Does the rewritten skill address the root cause? "
        "Answer COVERED or NOT_COVERED. "
        "Reply with JSON:\n"
        '[{"cluster_id": "...", "verdict": "COVERED"|"NOT_COVERED", "reason": "..."}, ...]\n'
    )
    return prompt
