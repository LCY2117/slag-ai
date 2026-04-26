from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import load_config
from .models import CarbonEconomyRequest, EvaluateRequest, ProjectPlanRequest, QARequest, RecommendRequest, StandardResponse
from .report import answer_question, generate_project_plan
from .rules import AGGREGATES, FORMING, SCENARIOS, carbon_economy, estimate_performance, recommend_formula

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
CONFIG = load_config(str(ROOT / "config.yaml"))

app = FastAPI(
    title="MSPC-GreenAI",
    description="钢渣基镁磷水泥透水建材智能设计与应用决策系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC / "index.html"))


@app.get("/api/health")
def health() -> Dict[str, Any]:
    sf = CONFIG.get("siliconflow", {})
    return {
        "ok": True,
        "app": "MSPC-GreenAI",
        "siliconflow_enabled": bool(sf.get("enabled")),
        "has_api_key": bool(sf.get("api_key")),
        "model": sf.get("model"),
        "base_url": sf.get("base_url"),
        "available_aggregates": AGGREGATES,
        "available_forming_methods": FORMING,
        "available_scenarios": SCENARIOS,
    }


@app.post("/api/recommend", response_model=StandardResponse)
def api_recommend(req: RecommendRequest):
    data = recommend_formula(**req.model_dump())
    return StandardResponse(ok=True, mode="rule", data=data, message="智能配方推荐完成")


@app.post("/api/evaluate", response_model=StandardResponse)
def api_evaluate(req: EvaluateRequest):
    data = estimate_performance(**req.model_dump())
    return StandardResponse(ok=True, mode="semi_empirical_rule", data=data, message="半经验性能评估完成")


@app.post("/api/carbon-economy", response_model=StandardResponse)
def api_carbon(req: CarbonEconomyRequest):
    data = carbon_economy(**req.model_dump())
    return StandardResponse(ok=True, mode="rule_calculation", data=data, message="节能减排测算完成")


@app.post("/api/project-plan", response_model=StandardResponse)
def api_project_plan(req: ProjectPlanRequest):
    data = generate_project_plan(req.model_dump(), CONFIG)
    return StandardResponse(ok=True, mode=data.get("generation_mode", "rule"), data=data, message="工程应用方案生成完成")


@app.post("/api/qa", response_model=StandardResponse)
def api_qa(req: QARequest):
    data = answer_question(req.question, CONFIG, use_llm=req.use_llm)
    return StandardResponse(ok=True, mode=data.get("mode", "rule"), data=data, message="项目问答完成")
