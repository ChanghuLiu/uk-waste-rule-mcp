from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

FACILITATOR = "https://facilitator.payai.network"
NETWORK = "eip155:8453"
PAY_TO = os.getenv("WASTE_X402_PAY_TO", "0xDAAef0FD525278aAD0bA11066A96c338642A3d1A")
PUBLIC_MCP_URL = "https://waste.regevidencehub.com/mcp"
EXPECTED_SERVICE_NAME = "RegEvidenceHub Waste"
EXPECTED_TAGS = ["waste", "england", "permit", "carrier", "compliance"]

def fetch_json(url: str, timeout: int = 20):
    req = Request(url, headers={"Accept":"application/json","User-Agent":"RegEvidenceHubWaste/0.2 payai-compat"})
    with urlopen(req, timeout=timeout) as response:
        return int(getattr(response, "status", 200)), json.loads(response.read().decode("utf-8"))

def main() -> None:
    status_supported, supported = fetch_json(FACILITATOR + "/supported")
    status_bazaar, bazaar = fetch_json(FACILITATOR + "/discovery/resources?type=mcp&limit=5")
    assert status_supported == 200
    text = json.dumps(supported, sort_keys=True).lower()
    assert NETWORK.lower() in text and "exact" in text, "PayAI /supported missing Base mainnet exact"
    assert status_bazaar == 200 and isinstance(bazaar, dict)

    os.environ["WASTE_X402_NETWORK"] = NETWORK
    os.environ["WASTE_X402_PAY_TO"] = PAY_TO
    os.environ["WASTE_X402_FACILITATOR_URL"] = FACILITATOR
    os.environ["WASTE_PUBLIC_MCP_URL"] = PUBLIC_MCP_URL
    os.environ["WASTE_PAYMENT_MODE"] = "paid"

    from uk_waste_rule_mcp.x402_mcp2 import MCP2X402Gate, PaidToolSpec

    executed = {"count": 0}
    def business_handler(_args):
        executed["count"] += 1
        return {"should_not_execute": True}

    gate = MCP2X402Gate()
    wrapped = gate.build(
        PaidToolSpec(
            name="waste_payai_compat_probe",
            price="$0.01",
            description="CI-only Waste PayAI x402 compatibility probe.",
            input_schema={"type":"object","properties":{"probe":{"type":"string"}},"additionalProperties":False},
            example={"probe":"compatibility"},
        ),
        business_handler,
    )
    result = wrapped({"probe":"compatibility"}, {"toolName":"waste_payai_compat_probe","_meta":{}})
    structured = getattr(result, "structured_content", None)
    if hasattr(structured, "model_dump"):
        structured = structured.model_dump(by_alias=True, exclude_none=True)
    assert isinstance(structured, dict) and structured.get("x402Version") == 2
    accepts = structured.get("accepts") or []
    base_exact = [x for x in accepts if isinstance(x,dict) and str(x.get("network"))==NETWORK and str(x.get("scheme"))=="exact"]
    assert base_exact
    terms = base_exact[0]
    assert str(terms.get("payTo","")).lower() == PAY_TO.lower()
    assert executed["count"] == 0
    resource = structured.get("resource") or {}
    assert resource.get("url") == PUBLIC_MCP_URL
    assert resource.get("serviceName") == EXPECTED_SERVICE_NAME
    assert resource.get("tags") == EXPECTED_TAGS
    assert len(EXPECTED_SERVICE_NAME) <= 32 and len(EXPECTED_TAGS) <= 5

    report = {
        "facilitator":FACILITATOR,"supported_http":status_supported,"bazaar_http":status_bazaar,
        "base_mainnet_exact":True,"unpaid_challenge_x402_v2":True,"challenge_network":NETWORK,
        "challenge_scheme":terms.get("scheme"),"challenge_asset":terms.get("asset"),
        "challenge_amount":terms.get("amount"),"challenge_pay_to":terms.get("payTo"),
        "business_handler_executions":executed["count"],"bazaar_resource":resource.get("url"),
        "bazaar_service_name":resource.get("serviceName"),"bazaar_tags":resource.get("tags"),
    }
    Path("/tmp/payai-compatibility.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report, sort_keys=True))

if __name__ == "__main__":
    main()
