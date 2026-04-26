from app.rules import carbon_economy, estimate_performance, recommend_formula


def test_optimal_rule():
    out = estimate_performance("MP", "VM", 25.0)
    assert out["estimated_performance"]["compressive_strength_mpa"] > 39
    assert out["scores"]["composite_score"] > 85


def test_recommend():
    out = recommend_formula("parking", "high", "high", "precast")
    assert out["recommended_parameters"]["aggregate_grade"] == "MP"


def test_carbon():
    out = carbon_economy(1000, 10)
    assert out["calculation"]["concrete_volume_m3"] == 100
    assert out["calculation"]["steel_slag_consumption_ton"] == 170
