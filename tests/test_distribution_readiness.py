from __future__ import annotations

import json
from pathlib import Path

from uk_waste_rule_mcp.x402_mcp2 import BAZAAR_TAGS, BAZAAR_SERVICE_NAME, DEFAULT_PUBLIC_MCP_URL

ROOT = Path(__file__).resolve().parents[1]

def test_registry_metadata_uses_branded_public_ai_surface():
    server=json.loads((ROOT/"server.json").read_text(encoding="utf-8"))
    assert server["name"]=="io.github.ChanghuLiu/uk-waste-rule-mcp"
    assert server["version"]=="0.2.0"
    assert server["repository"]["id"]=="1381814950"
    assert server["remotes"]==[{"type":"streamable-http","url":"https://waste.regevidencehub.com/ai/mcp"}]

def test_glama_ownership_metadata_is_present():
    glama=json.loads((ROOT/"glama.json").read_text(encoding="utf-8"))
    assert glama["maintainers"]==["ChanghuLiu"]

def test_payai_bazaar_metadata_is_bounded():
    assert DEFAULT_PUBLIC_MCP_URL=="https://waste.regevidencehub.com/mcp"
    assert BAZAAR_SERVICE_NAME=="RegEvidenceHub Waste"
    assert len(BAZAAR_SERVICE_NAME)<=32
    assert 1<=len(BAZAAR_TAGS)<=5
    assert len(set(BAZAAR_TAGS))==len(BAZAAR_TAGS)
