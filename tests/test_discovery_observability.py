from __future__ import annotations

from uk_waste_rule_mcp.discovery_observability import classify_source


def test_smithery_scanner_is_bounded_indexer_source():
    assert classify_source("SmitheryBot/1.0 (+https://smithery.ai)", "mcp_server_card") == ("smithery", "indexer")


def test_glama_scanner_is_bounded_indexer_source():
    assert classify_source("Glama-MCP-Scanner/1.0", "mcp_metadata") == ("glama", "indexer")


def test_openai_client_is_bounded_agent_source():
    assert classify_source("OpenAI-MCP/1.0", "public_ai_mcp") == ("openai", "agent")


def test_grok_client_is_bounded_agent_source():
    assert classify_source("xAI-Grok-MCP/1.0", "public_ai_mcp") == ("grok", "agent")


def test_generic_machine_client_is_unknown_machine():
    assert classify_source("python-httpx/0.28", "mcp_metadata") == ("unknown_machine", "unknown_machine")


def test_normal_browser_root_is_not_counted_as_machine():
    assert classify_source("Mozilla/5.0 Chrome/153.0", "root") is None
