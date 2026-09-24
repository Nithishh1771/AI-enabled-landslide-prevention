from services.risk_engine import classify_risk
from services.escalation import analyze_escalation

def test_risk_classes():
    assert classify_risk(10) == "LOW"
    assert classify_risk(40) == "MODERATE"
    assert classify_risk(60) == "HIGH"
    assert classify_risk(80) == "CRITICAL"

def test_rapid_escalation():
    result = analyze_escalation([{"risk_score":42},{"risk_score":55},{"risk_score":67},{"risk_score":82},{"risk_score":87}])
    assert result["status"] in {"RAPIDLY INCREASING","CRITICAL"}
