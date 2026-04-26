from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


OPTIMAL = {
    "aggregate_grade": "MP",
    "forming_method": "VM",
    "porosity_pct": 25.0,
    "water_binder_ratio": 0.16,
    "aggregate_binder_ratio": 4.8,
    "compressive_28d_mpa": 41.5,
    "flexural_28d_mpa": 8.0,
    "permeability_mm_s": 7.0,
    "steel_slag_consumption_kg_m3": 1700.0,
}

AGGREGATES = {
    "FP": {"name": "细粒级钢渣", "range": "2.5–5.0 mm", "min": 2.5, "max": 5.0},
    "MP": {"name": "中粒级钢渣", "range": "5.0–10.0 mm", "min": 5.0, "max": 10.0},
    "CP": {"name": "粗粒级钢渣", "range": "10.0–15.0 mm", "min": 10.0, "max": 15.0},
}

FORMING = {
    "TM": {"name": "夯实成型", "best_for": "现场小型施工", "constructability": 88},
    "VM": {"name": "振动成型", "best_for": "工厂预制/综合高性能", "constructability": 92},
    "HM": {"name": "静水压成型", "best_for": "高精度构件", "constructability": 72},
}

SCENARIOS = {
    "pedestrian": {"name": "人行步道", "target_strength": 25, "target_perm": 5.5},
    "parking": {"name": "停车场", "target_strength": 35, "target_perm": 6.0},
    "plaza": {"name": "城市广场", "target_strength": 30, "target_perm": 6.0},
    "heavy_road": {"name": "重载道路", "target_strength": 40, "target_perm": 5.8},
    "eco_slope": {"name": "生态护坡", "target_strength": 20, "target_perm": 6.5},
    "emergency_repair": {"name": "应急道路修复", "target_strength": 30, "target_perm": 5.5},
    "custom": {"name": "自定义工程", "target_strength": 30, "target_perm": 6.0},
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_code(value: str, allowed: Dict[str, Any], default: str) -> str:
    if not value:
        return default
    value = value.strip()
    upper = value.upper()
    if upper in allowed:
        return upper
    mapping = {
        "细粒级": "FP", "细": "FP", "FP": "FP",
        "中粒级": "MP", "中": "MP", "MP": "MP",
        "粗粒级": "CP", "粗": "CP", "CP": "CP",
        "夯实": "TM", "夯实成型": "TM", "TM": "TM",
        "振动": "VM", "振动成型": "VM", "VM": "VM",
        "静水压": "HM", "静水压成型": "HM", "HM": "HM",
    }
    return mapping.get(value, default)


def age_factor(age_day: float, kind: str = "compressive") -> float:
    # 1h = 0.0417d，MPC 具备快硬早强特性；这里使用平滑经验函数用于展示。
    if age_day <= 0.06:
        return 0.26 if kind == "compressive" else 0.30
    if age_day <= 1.1:
        return 0.56 if kind == "compressive" else 0.58
    # 对 1d 到 28d 进行对数增长，28d 归一为 1.0。
    val = 0.56 + 0.44 * math.log(max(age_day, 1.0)) / math.log(28.0)
    return clamp(val, 0.56, 1.08)


def porosity_strength_factor(porosity_pct: float, forming_method: str) -> float:
    # 项目核心：强度在约 25% 孔隙率附近出现协同最优，不采用传统线性负相关。
    distance = porosity_pct - OPTIMAL["porosity_pct"]
    curvature = 0.018 if forming_method in {"VM", "TM"} else 0.024
    return clamp(1.0 - curvature * distance * distance, 0.62, 1.03)


def porosity_permeability_factor(porosity_pct: float) -> float:
    # 透水性能随孔隙率增加而升高。
    return clamp(1.0 + 0.055 * (porosity_pct - OPTIMAL["porosity_pct"]), 0.65, 1.35)


def ratio_factor(value: float, optimal: float, sensitivity: float, min_factor: float = 0.82) -> float:
    return clamp(1.0 - sensitivity * abs(value - optimal), min_factor, 1.04)


def estimate_performance(
    aggregate_grade: str,
    forming_method: str,
    porosity_pct: float,
    water_binder_ratio: float = 0.16,
    aggregate_binder_ratio: float = 4.8,
    age_day: float = 28.0,
    scenario: str = "custom",
) -> Dict[str, Any]:
    agg = normalize_code(aggregate_grade, AGGREGATES, "MP")
    form = normalize_code(forming_method, FORMING, "VM")
    scene = SCENARIOS.get(scenario, SCENARIOS["custom"])

    strength_grade_factor = {
        "FP": 0.93,
        "MP": 1.00,
        "CP": 0.84,
    }[agg]
    if form == "HM":
        strength_grade_factor *= {"FP": 1.02, "MP": 0.95, "CP": 0.88}[agg]

    forming_strength_factor = {"VM": 1.00, "TM": 0.92, "HM": 0.86}[form]
    wbr_factor = ratio_factor(water_binder_ratio, OPTIMAL["water_binder_ratio"], 3.0, 0.84)
    abr_factor = ratio_factor(aggregate_binder_ratio, OPTIMAL["aggregate_binder_ratio"], 0.08, 0.86)
    p_strength = porosity_strength_factor(porosity_pct, form)

    compressive = (
        OPTIMAL["compressive_28d_mpa"]
        * age_factor(age_day, "compressive")
        * strength_grade_factor
        * forming_strength_factor
        * p_strength
        * wbr_factor
        * abr_factor
    )

    flexural_grade_factor = {"FP": 0.98, "MP": 1.00, "CP": 0.82}[agg]
    flexural = (
        OPTIMAL["flexural_28d_mpa"]
        * age_factor(age_day, "flexural")
        * flexural_grade_factor
        * {"VM": 1.00, "TM": 0.91, "HM": 0.84}[form]
        * clamp(1.0 - 0.012 * (porosity_pct - 25.0) ** 2, 0.72, 1.02)
        * wbr_factor
    )

    permeability = (
        OPTIMAL["permeability_mm_s"]
        * porosity_permeability_factor(porosity_pct)
        * {"FP": 0.92, "MP": 1.00, "CP": 1.08}[agg]
        * {"VM": 1.00, "TM": 1.04, "HM": 0.97}[form]
        * clamp(1.0 - 0.6 * max(0.0, OPTIMAL["water_binder_ratio"] - water_binder_ratio), 0.92, 1.05)
    )

    target_strength = scene["target_strength"]
    target_perm = scene["target_perm"]

    strength_score = clamp(compressive / target_strength * 100.0, 0, 105)
    permeability_score = clamp(permeability / target_perm * 100.0, 0, 105)
    porosity_score = clamp(100.0 - abs(porosity_pct - 25.0) * 18.0, 0, 100)
    constructability = FORMING[form]["constructability"]
    if scenario == "heavy_road" and form == "HM":
        constructability -= 12
    if scenario in {"pedestrian", "eco_slope"} and form == "TM":
        constructability += 4
    low_carbon_score = 95.0

    composite_score = (
        strength_score * 0.35
        + permeability_score * 0.30
        + porosity_score * 0.20
        + constructability * 0.10
        + low_carbon_score * 0.05
    )
    composite_score = clamp(composite_score, 0, 100)

    warnings: List[str] = []
    if abs(porosity_pct - 25.0) > 2.0:
        warnings.append("孔隙率偏离 25% 协同最优控制点，需重点复核强度与透水平衡。")
    if agg == "CP" and scenario in {"parking", "heavy_road"}:
        warnings.append("粗粒级钢渣有利于透水，但重载或停车场场景下需复核力学强度。")
    if form == "HM":
        warnings.append("静水压成型适合高精度构件，作为大面积铺装工艺时需评估设备和施工效率。")
    if water_binder_ratio > 0.19:
        warnings.append("水胶比较高可能影响早强和浆体包裹稳定性。")

    recommendation_level = "强烈推荐" if composite_score >= 88 else "推荐" if composite_score >= 75 else "谨慎采用" if composite_score >= 60 else "不建议"

    return {
        "input": {
            "aggregate_grade": agg,
            "aggregate_name": AGGREGATES[agg]["name"],
            "aggregate_range": AGGREGATES[agg]["range"],
            "forming_method": form,
            "forming_name": FORMING[form]["name"],
            "porosity_pct": round(porosity_pct, 2),
            "water_binder_ratio": round(water_binder_ratio, 3),
            "aggregate_binder_ratio": round(aggregate_binder_ratio, 2),
            "age_day": age_day,
            "scenario": scene["name"],
        },
        "estimated_performance": {
            "compressive_strength_mpa": round(compressive, 2),
            "flexural_strength_mpa": round(flexural, 2),
            "permeability_mm_s": round(permeability, 2),
        },
        "scores": {
            "strength_score": round(strength_score, 1),
            "permeability_score": round(permeability_score, 1),
            "porosity_score": round(porosity_score, 1),
            "constructability_score": round(constructability, 1),
            "low_carbon_score": round(low_carbon_score, 1),
            "composite_score": round(composite_score, 1),
            "recommendation_level": recommendation_level,
        },
        "warnings": warnings,
        "explanation_points": explain_evaluation(agg, form, porosity_pct, scenario),
    }


def explain_evaluation(agg: str, form: str, porosity_pct: float, scenario: str) -> List[str]:
    points = []
    if agg == "MP":
        points.append("中粒级钢渣位于项目综合最优粒径区间，有利于兼顾强度与连通孔隙。")
    elif agg == "CP":
        points.append("粗粒级钢渣有利于形成更畅通的孔隙结构，透水性较强，但强度需重点复核。")
    else:
        points.append("细粒级钢渣浆体包裹更充分，但孔隙连通性可能弱于中粗粒级。")

    if form == "VM":
        points.append("振动成型为项目综合推荐工艺，适合工厂预制和高性能铺装。")
    elif form == "TM":
        points.append("夯实成型设备要求低，适合现场小型施工，但强度稳定性需通过工艺控制保证。")
    else:
        points.append("静水压成型适合高精度构件，工程规模化铺装时应评估设备适配性。")

    if abs(porosity_pct - 25.0) <= 1.0:
        points.append("孔隙率接近 25% 协同最优控制点，有利于同时保持透水性和力学性能。")
    elif porosity_pct > 25.0:
        points.append("孔隙率高于 25%，透水性能通常增强，但强度可能出现折减。")
    else:
        points.append("孔隙率低于 25%，强度可能较稳定，但透水能力可能受到限制。")

    return points


def recommend_formula(
    scenario: str = "parking",
    strength_requirement: str = "high",
    permeability_requirement: str = "high",
    construction_mode: str = "precast",
    cost_priority: str = "balanced",
    notes: str = "",
) -> Dict[str, Any]:
    scene_key = scenario if scenario in SCENARIOS else "custom"
    scene = SCENARIOS[scene_key]
    strength = (strength_requirement or "high").lower()
    perm = (permeability_requirement or "high").lower()
    construction = (construction_mode or "precast").lower()

    agg = "MP"
    form = "VM"
    porosity = 25.0

    if scene_key in {"heavy_road", "parking"} or strength in {"very_high", "high"}:
        agg, form, porosity = "MP", "VM", 25.0
    if perm == "very_high" and scene_key not in {"heavy_road"}:
        # 高透水需求下，给出更偏透水的备选；主推荐仍优先保持综合性能。
        porosity = 25.8
        if strength == "normal" and scene_key in {"eco_slope", "pedestrian"}:
            agg = "CP"
    if construction == "onsite" and scene_key not in {"heavy_road"}:
        form = "TM"
    if construction == "high_precision":
        form = "HM"
        if strength in {"high", "very_high"}:
            agg = "FP"
            porosity = 24.5
    if cost_priority == "performance":
        agg, form, porosity = "MP", "VM", 25.0

    perf = estimate_performance(
        aggregate_grade=agg,
        forming_method=form,
        porosity_pct=porosity,
        water_binder_ratio=0.16,
        aggregate_binder_ratio=4.8,
        age_day=28.0,
        scenario=scene_key,
    )

    alternatives = []
    if not (agg == "MP" and form == "VM"):
        alternatives.append(estimate_performance("MP", "VM", 25.0, scenario=scene_key))
    if perm in {"high", "very_high"}:
        alternatives.append(estimate_performance("CP", "TM" if construction == "onsite" else "VM", 26.0, scenario=scene_key))
    if construction == "onsite":
        alternatives.append(estimate_performance("MP", "TM", 25.2, scenario=scene_key))

    summary = build_recommendation_summary(perf, scene_key, strength, perm, construction, cost_priority)
    return {
        "scene": scene,
        "primary_recommendation": perf,
        "recommended_parameters": {
            "aggregate_grade": agg,
            "aggregate_name": AGGREGATES[agg]["name"],
            "aggregate_range": AGGREGATES[agg]["range"],
            "forming_method": form,
            "forming_name": FORMING[form]["name"],
            "porosity_control_pct": f"{porosity - 0.7:.1f}–{porosity + 0.7:.1f}",
            "water_binder_ratio": 0.16,
            "aggregate_binder_ratio": 4.8,
        },
        "alternatives": alternatives[:3],
        "summary": summary,
        "next_steps": [
            "按推荐粒径筛分钢渣并控制杂质含量。",
            "以 25% 左右有效孔隙率为核心控制点进行试拌。",
            "针对目标工程进行 1h、1d、28d 强度与透水复核。",
            "将实测数据录入系统，逐步校准半经验模型。",
        ],
    }


def build_recommendation_summary(perf: Dict[str, Any], scene_key: str, strength: str, perm: str, construction: str, cost_priority: str) -> str:
    inp = perf["input"]
    est = perf["estimated_performance"]
    score = perf["scores"]
    return (
        f"针对{SCENARIOS.get(scene_key, SCENARIOS['custom'])['name']}场景，系统推荐采用"
        f"{inp['aggregate_name']}（{inp['aggregate_range']}）+{inp['forming_name']}，"
        f"孔隙率控制在约 {inp['porosity_pct']}%。该方案预计 28d 抗压强度约"
        f" {est['compressive_strength_mpa']} MPa，抗折强度约 {est['flexural_strength_mpa']} MPa，"
        f"透水系数约 {est['permeability_mm_s']} mm/s，综合评分 {score['composite_score']} 分。"
        f"推荐逻辑是优先贴近中粒级钢渣、振动成型和 25% 孔隙率这一综合最优工况。"
    )


def carbon_economy(area_m2: float, thickness_cm: float, steel_slag_consumption_kg_m3: float = 1700.0,
                   raw_material_cost_saving_pct: float = 30.0,
                   construction_maintenance_saving_pct: float = 40.0) -> Dict[str, Any]:
    volume_m3 = area_m2 * (thickness_cm / 100.0)
    slag_kg = volume_m3 * steel_slag_consumption_kg_m3
    slag_ton = slag_kg / 1000.0
    return {
        "input": {
            "area_m2": area_m2,
            "thickness_cm": thickness_cm,
            "steel_slag_consumption_kg_m3": steel_slag_consumption_kg_m3,
        },
        "calculation": {
            "concrete_volume_m3": round(volume_m3, 2),
            "steel_slag_consumption_kg": round(slag_kg, 2),
            "steel_slag_consumption_ton": round(slag_ton, 2),
            "estimated_natural_aggregate_replacement_ton": round(slag_ton, 2),
            "raw_material_cost_saving_pct_reference": raw_material_cost_saving_pct,
            "construction_maintenance_saving_pct_reference": construction_maintenance_saving_pct,
        },
        "summary": (
            f"按铺装面积 {area_m2:g} m²、厚度 {thickness_cm:g} cm 估算，混凝土体积约 "
            f"{volume_m3:.2f} m³；若按每立方消纳钢渣 {steel_slag_consumption_kg_m3:g} kg 计算，"
            f"预计可资源化利用钢渣约 {slag_ton:.2f} 吨，并相应减少天然骨料开采与钢渣堆存压力。"
        ),
    }


def compact_context_for_llm() -> str:
    return (
        "项目知识：MSPC 为镁磷水泥钢渣透水混凝土，以复配镁磷水泥为胶凝材料，以工业固废钢渣为粗骨料。"
        "综合最优工况为中粒级钢渣 5.0–10.0mm + 振动成型 + 约25%有效孔隙率，"
        "推荐水胶比0.16，骨料胶凝比4.8。典型最优性能为28d抗压强度41.5MPa、抗折强度8.0MPa、"
        "透水系数约7.0mm/s。每立方混凝土约消纳钢渣1700kg。系统输出应避免夸大，说明当前为规则约束型原型。"
    )
