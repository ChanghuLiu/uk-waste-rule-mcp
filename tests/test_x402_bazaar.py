from __future__ import annotations

import inspect

from uk_waste_rule_mcp.x402_mcp2 import MCP2X402Gate


def test_bazaar_resource_server_extension_is_registered_before_initialize():
    source = inspect.getsource(MCP2X402Gate.__init__)
    assert "bazaar_resource_server_extension" in source
    assert "register_extension(bazaar_resource_server_extension)" in source
    assert source.index("register_extension(bazaar_resource_server_extension)") < source.index("initialize()")


def test_installed_x402_supports_mcp_output_examples():
    from x402.extensions.bazaar import (
        DeclareMcpDiscoveryConfig,
        OutputConfig,
        declare_mcp_discovery_extension,
    )

    extension = declare_mcp_discovery_extension(
        DeclareMcpDiscoveryConfig(
            tool_name="waste_rule_preflight",
            description="Waste route preflight",
            transport="streamable-http",
            input_schema={"type":"object","properties":{"nation":{"type":"string"}}},
            example={"nation":"England"},
            output=OutputConfig(example={
                "decision":{"route":"PERMIT_OR_EXEMPTION_AND_DIGITAL_TRACKING_REVIEW","status":"SCREENING_COMPLETE_REVIEW_REQUIRED"}
            }),
        )
    )
    assert extension["bazaar"]["info"]["output"]["type"] == "json"
    assert extension["bazaar"]["info"]["output"]["example"]["decision"]["route"] == "PERMIT_OR_EXEMPTION_AND_DIGITAL_TRACKING_REVIEW"
