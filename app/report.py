from __future__ import annotations

import re
from typing import Any, Dict, List

from .llm import siliconflow_chat
from .rules import carbon_economy, compact_context_for_llm, recommend_formula


META_COMMENT_PATTERNS = [
    r"^以上方案.*(?:答辩|推广).*?$",
    r"^本方案.*(?:结构清晰|逻辑严谨|适用于|可用于).*$",
    r"^该方案.*(?:结构清晰|逻辑严谨|适用于|可用于).*$",
    r"^以上内容.*(?:结构清晰|逻辑严谨|适用于|可用于).*$",
]

CHINESE_NUMERAL_MARKERS = set("一二三四五六七八九十")


def normalize_list_marker_noise(line: str) -> str:
    """Normalize accidental one-char list markers (e.g. '囁.') to bullets."""
    m = re.match(r"^(\s*)([\u3400-\u9fff])\.\s+(.*)$", line)
    if not m:
        return line
    indent, marker, content = m.groups()
    if marker in CHINESE_NUMERAL_MARKERS:
        return line
    return f"{indent}- {content}"


def clean_project_plan_markdown(markdown: str) -> str:
    lines = []
    for line in str(markdown or "").splitlines():
        line = normalize_list_marker_noise(line)
        stripped = line.strip()
        if any(re.search(pattern, stripped) for pattern in META_COMMENT_PATTERNS):
            continue
        lines.append(line.rstrip())

    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"(?m)^# (.+)$", r"## \1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"(?m)^([ \t]*)[-*]\s*$\n?", "", cleaned)
    return cleaned


def offline_project_plan(req: Dict[str, Any], rec: Dict[str, Any], eco: Dict[str, Any]) -> str:
    params = rec["recommended_parameters"]
    perf = rec["primary_recommendation"]["estimated_performance"]
    score = rec["primary_recommendation"]["scores"]
    goals = "、".join(req.get("goals", [])) or "排水、低碳、耐久"
    return f"""
## 工程应用方案建议

### 1. 工程概况
项目类型：{req.get('project_type', '工程铺装')}；地点：{req.get('location', '未指定')}；面积：{req.get('area_m2')} m²；设计厚度：{req.get('thickness_cm')} cm。主要目标为：{goals}。

### 2. 推荐材料与工艺
建议采用 {params['aggregate_name']}（{params['aggregate_range']}）+ {params['forming_name']}，孔隙率控制在 {params['porosity_control_pct']}，水胶比建议为 {params['water_binder_ratio']}，骨料胶凝比建议为 {params['aggregate_binder_ratio']}。

### 3. 预计性能
半经验评估结果显示，该方案 28d 抗压强度约 {perf['compressive_strength_mpa']} MPa，抗折强度约 {perf['flexural_strength_mpa']} MPa，透水系数约 {perf['permeability_mm_s']} mm/s，综合推荐评分为 {score['composite_score']} 分，推荐等级为“{score['recommendation_level']}”。

### 4. 节能减排效益
{eco['summary']} 该方案有助于减少天然骨料开采、降低钢渣堆存环境压力，并提升海绵城市铺装的排水能力。

### 5. 施工建议
施工前应进行试拌与试铺，重点复核有效孔隙率、抗压强度、抗折强度和透水系数。若用于停车场或重载道路，应增加承载与耐久性验证。

### 6. 说明
本方案由 MSPC-GreenAI 规则约束型原型系统生成，适合用于前期方案比选、项目展示和答辩说明，正式工程应用仍需结合检测报告和设计规范进行复核。
""".strip()


def generate_project_plan(req: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    rec = recommend_formula(
        scenario="parking" if "车" in req.get("project_type", "") else "pedestrian",
        strength_requirement=req.get("strength_requirement", "high"),
        permeability_requirement=req.get("permeability_requirement", "high"),
        construction_mode=req.get("construction_mode", "precast"),
    )
    eco = carbon_economy(req.get("area_m2", 1000), req.get("thickness_cm", 10))
    fallback = offline_project_plan(req, rec, eco)
    messages = [
        {
            "role": "system",
            "content": (
                "你是绿色建材工程方案专家。只输出工程方案正文，必须基于给定规则和计算结果，"
                "不能夸大，不能编造检测数据，不能改写或替换推荐粒径、成型方式、孔隙率、水胶比、骨料胶凝比。"
                "禁止输出自我评价、适用性评价、写作评价或总结式套话，"
                "例如“结构清晰”“逻辑严谨”“适用于项目答辩或推广使用”。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"{compact_context_for_llm()}\n\n"
                f"工程输入：{req}\n\n推荐结果：{rec}\n\n节能减排计算：{eco}\n\n"
                "请生成一份可直接展示的工程应用方案正文。硬性格式要求：\n"
                "1. 只允许输出以下六个二级标题：工程概况、推荐材料与工艺、预计性能、节能减排效益、施工控制要点、工程复核要点。\n"
                "2. 推荐材料与工艺中的粒径、成型方式、孔隙率、水胶比、骨料胶凝比必须逐字使用推荐结果，不得自行推断。\n"
                "3. 使用 Markdown 二级标题和项目符号列表，不要使用表格，不要插入多余空行。\n"
                "4. 最后一节只能写“工程复核要点”，列出实测和规范复核事项。\n"
                "5. 不要写“以上方案”“本方案结构清晰”“适用于答辩/推广”“下一步工作”等元评价或过程性标题。"
            ),
        },
    ]
    llm = siliconflow_chat(messages, config, fallback=fallback)
    plan_markdown = clean_project_plan_markdown(llm.content)
    return {
        "recommendation": rec,
        "carbon_economy": eco,
        "plan_markdown": plan_markdown,
        "generation_mode": llm.get("mode"),
        "llm_error": llm.get("error", ""),
    }


def offline_qa_answer(question: str) -> str:
    q = question or ""
    if "25" in q or "孔隙" in q:
        return "25% 左右有效孔隙率是本项目的关键控制点。系统规则认为，在该区间附近，MSPC 可以同时保持较好的连通孔隙和较高的胶结骨架强度，从而实现强度与透水性能的协同平衡。"
    if "钢渣" in q:
        return "钢渣作为工业固废可替代天然骨料，具有较高强度和耐磨性，并能减少天然砂石开采与固废堆存压力，是本项目低碳与资源化利用价值的核心来源。"
    if "镁磷" in q or "MPC" in q:
        return "镁磷水泥具有快硬早强、粘结强度高、体积稳定性较好等特点。将其用于透水混凝土，可提升钢渣骨料之间的胶结能力，缓解传统透水混凝土强度不足的问题。"
    if "最优" in q:
        return "本项目规则库将“中粒级钢渣 5.0–10.0mm + 振动成型 + 约25%孔隙率”作为综合最优工况，典型性能锚点为 28d 抗压强度约41.5MPa、抗折强度约8.0MPa、透水系数约7.0mm/s。"
    return "MSPC-GreenAI 当前采用规则约束型 AI 原型：把材料实验规律转化为专家规则，再结合大模型 API 生成解释、方案和推广文本。它适合用于前期方案推荐、答辩展示和数据闭环积累。"


def answer_question(question: str, config: Dict[str, Any], use_llm: bool = True) -> Dict[str, Any]:
    fallback = offline_qa_answer(question)
    if not use_llm:
        return {"answer": fallback, "mode": "offline_rule"}
    messages = [
        {"role": "system", "content": "你是 MSPC-GreenAI 项目答辩助手。回答要准确、简洁、专业，不要编造未给出的实验数据。"},
        {"role": "user", "content": f"{compact_context_for_llm()}\n\n用户问题：{question}\n\n请用中文回答，适合比赛答辩或项目展示。"},
    ]
    llm = siliconflow_chat(messages, config, fallback=fallback)
    return {"answer": llm.content, "mode": llm.get("mode"), "llm_error": llm.get("error", "")}
