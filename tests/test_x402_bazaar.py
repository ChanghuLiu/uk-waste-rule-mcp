from __future__ import annotations

import inspect

from uk_waste_rule_mcp.x402_mcp2 import MCP2X402Gate


def test_bazaar_resource_server_extension_is_registered_before_initialize():
    source = inspect.getsource(MCP2X402Gate.__init__)
    assert "bazaar_resource_server_extension" in source
    assert "register_extension(bazaar_resource_server_extension)" in source
    assert source.index("register_extension(bazaar_resource_server_extension)") < source.index("initialize()")
