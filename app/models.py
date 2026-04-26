from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    scenario: str = Field(default="parking", description="工程场景：pedestrian/parking/plaza/heavy_road/eco_slope/emergency_repair/custom")
    strength_requirement: str = Field(default="high", description="强度需求：normal/high/very_high")
    permeability_requirement: str = Field(default="high", description="透水需求：normal/high/very_high")
    construction_mode: str = Field(default="precast", description="施工方式：onsite/precast/high_precision")
    cost_priority: str = Field(default="balanced", description="成本优先级：low_cost/balanced/performance")
    notes: str = ""


class EvaluateRequest(BaseModel):
    aggregate_grade: str = Field(default="MP", description="FP/MP/CP")
    forming_method: str = Field(default="VM", description="TM/VM/HM")
    porosity_pct: float = Field(default=25.0, ge=18.0, le=35.0)
    water_binder_ratio: float = Field(default=0.16, ge=0.08, le=0.30)
    aggregate_binder_ratio: float = Field(default=4.8, ge=2.5, le=7.0)
    age_day: float = Field(default=28.0, ge=0.04, le=365.0)
    scenario: str = "parking"


class CarbonEconomyRequest(BaseModel):
    area_m2: float = Field(default=1000, gt=0)
    thickness_cm: float = Field(default=10, gt=0)
    steel_slag_consumption_kg_m3: float = Field(default=1700, gt=0)
    raw_material_cost_saving_pct: float = Field(default=30, ge=0, le=100)
    construction_maintenance_saving_pct: float = Field(default=40, ge=0, le=100)


class ProjectPlanRequest(BaseModel):
    project_type: str = Field(default="校园停车场")
    area_m2: float = Field(default=1000, gt=0)
    thickness_cm: float = Field(default=10, gt=0)
    location: str = Field(default="校园")
    goals: List[str] = Field(default_factory=lambda: ["排水", "低碳", "耐久"])
    strength_requirement: str = "high"
    permeability_requirement: str = "high"
    construction_mode: str = "precast"
    extra_requirements: str = ""


class QARequest(BaseModel):
    question: str = Field(default="为什么 25% 孔隙率重要？")
    use_llm: bool = True


class StandardResponse(BaseModel):
    ok: bool = True
    mode: str = "rule"
    data: Dict[str, Any]
    message: str = ""
