"""Safe diagnostic tool execution engine for TraceMind.

Implements a fixed whitelist of read-only diagnostic functions with strict Pydantic
argument validation. Prevents arbitrary execution, injection, and destructive commands.
"""

import os
import re
import json
from typing import Dict, Any, List
from pydantic import ValidationError

from .schemas import (
    ErrorSignatureArgs,
    CheckConfigKeysArgs,
    SearchIncidentsArgs,
    CheckLogPatternArgs,
)
from .log_parser import extract_signatures

# Path to incident dataset for local historical lookup
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
INCIDENTS_FILE = os.path.join(DATA_DIR, "incidents.jsonl")


def extract_error_signature(logs: str) -> Dict[str, Any]:
    """Scans logs for common error signatures (Exceptions, FATAL, ERROR, timeouts)."""
    signatures = extract_signatures(logs)
    return {
        "status": "success",
        "signatures_found": signatures,
        "count": len(signatures),
    }


def check_config_keys(logs: str, keys: List[str]) -> Dict[str, Any]:
    """Checks whether specific configuration keys or environment variables appear in logs."""
    found = []
    missing_context = []
    for key in keys:
        if key in logs:
            found.append(key)
            # Find surrounding snippet
            match = re.search(rf"[^\n\r]*{re.escape(key)}[^\n\r]*", logs)
            if match:
                missing_context.append(match.group(0).strip())

    return {
        "status": "success",
        "keys_checked": keys,
        "keys_found": found,
        "snippets": missing_context[:5],
    }


def search_historical_incidents(keyword: str, top_k: int = 3) -> Dict[str, Any]:
    """Performs a direct keyword filter over the raw incidents dataset."""
    matches = []
    if os.path.exists(INCIDENTS_FILE):
        kw_lower = keyword.lower()
        with open(INCIDENTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                searchable = (
                    f"{record.get('title', '')} "
                    f"{record.get('description', '')} "
                    f"{record.get('root_cause', '')} "
                    f"{record.get('related_logs', '')}"
                ).lower()
                if kw_lower in searchable:
                    matches.append({
                        "id": f"incident_{record.get('id')}",
                        "title": record.get("title"),
                        "root_cause": record.get("root_cause"),
                    })
                if len(matches) >= top_k:
                    break

    return {
        "status": "success",
        "keyword": keyword,
        "match_count": len(matches),
        "results": matches,
    }


def check_log_patterns(logs: str, pattern: str) -> Dict[str, Any]:
    """Safely searches logs for a specified regex or text pattern."""
    # Guard against regex denial of service / complexity
    if len(pattern) > 200:
        return {"status": "error", "message": "Pattern exceeds maximum allowed length of 200 characters."}

    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        matches = compiled.findall(logs)
        return {
            "status": "success",
            "pattern": pattern,
            "match_count": len(matches),
            "sample_matches": [str(m)[:150] for m in matches[:5]],
        }
    except re.error as e:
        return {"status": "error", "message": f"Invalid regex pattern: {str(e)}"}


# Whitelist mapping of tools to implementation functions and Pydantic argument schemas
TOOL_REGISTRY = {
    "extract_error_signature": {
        "func": extract_error_signature,
        "schema": ErrorSignatureArgs,
        "description": "Extracts standard exception signatures and error lines from logs.",
    },
    "check_config_keys": {
        "func": check_config_keys,
        "schema": CheckConfigKeysArgs,
        "description": "Checks if specific config keys or environment variables appear in logs.",
    },
    "search_historical_incidents": {
        "func": search_historical_incidents,
        "schema": SearchIncidentsArgs,
        "description": "Searches incident history directly for matching keywords.",
    },
    "check_log_patterns": {
        "func": check_log_patterns,
        "schema": CheckLogPatternArgs,
        "description": "Searches logs using a regex or keyword pattern.",
    },
}


def get_available_tool_definitions() -> List[Dict[str, Any]]:
    """Returns metadata for all whitelisted tools."""
    return [
        {
            "name": name,
            "description": info["description"],
            "parameters": info["schema"].model_json_schema(),
        }
        for name, info in TOOL_REGISTRY.items()
    ]


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely executes a whitelisted diagnostic tool.
    Strictly validates arguments against the corresponding Pydantic schema.
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "status": "error",
            "tool_name": tool_name,
            "message": f"Tool '{tool_name}' is not whitelisted. Execution refused.",
        }

    meta = TOOL_REGISTRY[tool_name]
    arg_schema = meta["schema"]
    func = meta["func"]

    # Validate arguments with Pydantic
    try:
        validated_args = arg_schema(**arguments)
    except ValidationError as e:
        return {
            "status": "error",
            "tool_name": tool_name,
            "message": f"Invalid arguments provided for tool '{tool_name}'.",
            "details": e.errors(),
        }
    except Exception as e:
        return {
            "status": "error",
            "tool_name": tool_name,
            "message": f"Argument parsing failed: {str(e)}",
        }

    # Execute whitelisted function safely
    try:
        result = func(**validated_args.model_dump())
        return {
            "status": "success",
            "tool_name": tool_name,
            "output": result,
        }
    except Exception as e:
        return {
            "status": "error",
            "tool_name": tool_name,
            "message": f"Execution error in '{tool_name}': {str(e)}",
        }
