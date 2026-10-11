"""Unit tests for whitelisted diagnostic tools in src/tools.py."""

import pytest
from src.tools import execute_tool, get_available_tool_definitions


def test_get_available_tool_definitions():
    tools = get_available_tool_definitions()
    assert len(tools) == 4
    tool_names = [t["name"] for t in tools]
    assert "extract_error_signature" in tool_names
    assert "check_config_keys" in tool_names
    assert "search_historical_incidents" in tool_names
    assert "check_log_patterns" in tool_names


def test_extract_error_signature_tool():
    logs = "INFO Starting\nFATAL: connection to database failed\nERROR: timeout occurred"
    result = execute_tool("extract_error_signature", {"logs": logs})
    assert result["status"] == "success"
    assert result["tool_name"] == "extract_error_signature"
    assert result["output"]["count"] >= 2


def test_check_config_keys_tool():
    logs = "KeyError: 'INVENTORY_DB_URL' not found in environment variables."
    result = execute_tool(
        "check_config_keys",
        {"logs": logs, "keys": ["INVENTORY_DB_URL", "STRIPE_SECRET"]}
    )
    assert result["status"] == "success"
    assert "INVENTORY_DB_URL" in result["output"]["keys_found"]
    assert "STRIPE_SECRET" not in result["output"]["keys_found"]


def test_search_historical_incidents_tool():
    result = execute_tool(
        "search_historical_incidents",
        {"keyword": "timeout", "top_k": 2}
    )
    assert result["status"] == "success"
    assert result["output"]["match_count"] >= 1
    assert any("INC-001" in item["id"] for item in result["output"]["results"])


def test_check_log_patterns_tool():
    logs = "User 123 failed login\nUser 456 failed login"
    result = execute_tool(
        "check_log_patterns",
        {"logs": logs, "pattern": r"User \d+ failed"}
    )
    assert result["status"] == "success"
    assert result["output"]["match_count"] == 2


def test_tool_rejection_for_unlisted_name():
    result = execute_tool("system_shell_exec", {"cmd": "rm -rf /"})
    assert result["status"] == "error"
    assert "not whitelisted" in result["message"]


def test_tool_rejection_for_invalid_arguments():
    # check_config_keys requires 'logs' and 'keys'
    result = execute_tool("check_config_keys", {"logs": "some logs"})
    assert result["status"] == "error"
    assert "Invalid arguments" in result["message"]
