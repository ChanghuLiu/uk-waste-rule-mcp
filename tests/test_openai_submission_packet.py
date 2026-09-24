from __future__ import annotations

import json
from pathlib import Path

from uk_waste_rule_mcp.public_ai_server import PUBLIC_AI_TOOL_NAMES

ROOT = Path(__file__).resolve().parents[1]

def test_openai_submission_packet_matches_live_public_ai_contract():
    packet=json.loads((ROOT/"chatgpt-app-submission.json").read_text(encoding="utf-8"))
    assert packet["schema_version"]==1
    assert packet["app_info"]["display_name"]=="RegEvidenceHub Waste"
    assert list(packet["tools"])==list(PUBLIC_AI_TOOL_NAMES)
    assert len(packet["test_cases"])==5
    assert len(packet["negative_test_cases"])==3
    for name,tool in packet["tools"].items():
        assert tool["annotations"]=={"readOnlyHint":True,"openWorldHint":False,"destructiveHint":False},name
        assert all(tool["justifications"].values())

def test_openai_submission_packet_has_no_commercial_endpoint_or_payment_steering():
    raw=(ROOT/"chatgpt-app-submission.json").read_text(encoding="utf-8").lower()
    assert "https://waste.regevidencehub.com/mcp" not in raw
    assert "stripe" not in raw
    assert "private key" not in raw
    assert "seed phrase" not in raw
