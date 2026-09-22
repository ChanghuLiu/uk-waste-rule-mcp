"""MCP transport for the UK Waste Rule and Permit Change-Impact service."""

from __future__ import annotations

from typing import Any

from . import __version__
from .engine import PRODUCT, classify_waste_route, list_waste_rules, permit_change_impact, waste_preflight
from .monitor import check_all_sources, source_health, write_registry
from .sources import source_registry

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:  # pragma: no cover
    MCPServer = None  # type: ignore[assignment,misc]


if MCPServer is not None:
    mcp = MCPServer(name=PRODUCT, version=__version__)

    @mcp.tool()
    def waste_rule_preflight(scenario: dict[str, Any]) -> dict[str, Any]:
        """Run a conservative England waste-rule and authorisation preflight."""

        return waste_preflight(scenario)

    @mcp.tool()
    def classify_waste_route_tool(scenario: dict[str, Any]) -> dict[str, Any]:
        """Route a waste activity to permit, exemption, duty-of-care or review paths."""

        return classify_waste_route(scenario)

    @mcp.tool()
    def permit_change_impact_tool(scenario: dict[str, Any]) -> dict[str, Any]:
        """Screen whether supplied current/proposed facts require a permit-change review."""

        return permit_change_impact(scenario)

    @mcp.tool()
    def list_waste_rules_tool() -> dict[str, Any]:
        """List modelled roles, activities and bounded routes."""

        return list_waste_rules()

    @mcp.tool()
    def get_source_registry() -> list[dict[str, Any]]:
        """Return the official source registry and freshness dates."""

        return source_registry()

    @mcp.tool()
    def waste_source_status() -> dict[str, Any]:
        """Return the persisted official-source fingerprint and freshness gate."""

        return source_health()

    @mcp.tool()
    def check_waste_sources() -> dict[str, Any]:
        """Fetch monitored official sources and return current fingerprint comparisons."""

        checked = check_all_sources()
        return source_health(checked) | {"checked_sources": checked}

    @mcp.tool()
    def get_service_status() -> dict[str, Any]:
        """Return service metadata without running a regulatory decision."""

        return {
            "product": PRODUCT,
            "version": __version__,
            "scope": "England only",
            "status": "local_mvp",
            "decision_tools": ["waste_rule_preflight", "classify_waste_route_tool", "permit_change_impact_tool"],
            "free_discovery_tools": ["list_waste_rules_tool", "get_source_registry", "waste_source_status", "check_waste_sources", "get_service_status"],
            "source_health": source_health(),
            "commercial_layer": "not configured in local MVP",
        }


def main() -> None:
    if MCPServer is None:
        raise SystemExit("Install the MCP extra first: pip install -e '.[mcp]'")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
