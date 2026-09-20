"""MCP Integration layer for market intelligence queries."""
from typing import Dict, Any, List, Optional
from backend.core.logging import logger


class MarketIntelligenceMCP:
    """
    Exposes market context, indicators, and account statistics to external MCP clients
    WITHOUT allowing MCP tool calls to bypass the deterministic risk engine.
    """
    def __init__(self):
        pass

    def get_supported_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "get_market_quote",
                "description": "Fetch latest OHLCV and indicator summary for a tracked symbol",
                "parameters": {
                    "type": "object",
                    "properties": {"symbol": {"type": "string"}},
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_active_signals",
                "description": "Fetch currently detected technical patterns and strategy signals",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "get_risk_summary",
                "description": "Fetch active risk engine limits, drawdown status, and kill switch state",
                "parameters": {"type": "object", "properties": {}}
            }
        ]

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Strictly read-only tools exposed via MCP.
        # Order placement is NOT exposed via MCP directly to uphold the financial safety chain.
        if tool_name == "get_market_quote":
            return {"status": "success", "data": f"Quote for {arguments.get('symbol')}"}
        elif tool_name == "get_active_signals":
            return {"status": "success", "signals": []}
        elif tool_name == "get_risk_summary":
            return {"status": "success", "mode": "PAPER", "kill_switch": False}
        else:
            return {"status": "error", "message": f"Tool '{tool_name}' not permitted or unknown"}
