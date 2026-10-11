"""Unit tests for src/log_parser.py."""

import pytest
from src.log_parser import (
    mask_credentials,
    truncate_input,
    extract_signatures,
    format_untrusted_block,
    MAX_LOG_LENGTH,
)


def test_mask_credentials_bearer_token():
    raw = "Authorization: Bearer secret_token_value_abc1234567890xyz and more"
    sanitized, count = mask_credentials(raw)
    assert count >= 1
    assert "secret_token_value_abc1234567890xyz" not in sanitized
    assert "[REDACTED_BEARER_TOKEN]" in sanitized


def test_mask_credentials_database_url():
    raw = "Connecting to postgres://admin_user:superSecretPass123@prod-db.internal:5432/orders"
    sanitized, count = mask_credentials(raw)
    assert count >= 1
    assert "superSecretPass123" not in sanitized
    assert "[REDACTED_PASSWORD]" in sanitized
    assert "prod-db.internal:5432/orders" in sanitized


def test_mask_credentials_api_key():
    raw = "Config loaded: api_key='ak_live_998877665544332211'"
    sanitized, count = mask_credentials(raw)
    assert count >= 1
    assert "ak_live_998877665544332211" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_truncate_input():
    short_text = "Standard error line"
    truncated, was_cut = truncate_input(short_text, 100)
    assert not was_cut
    assert truncated == short_text

    long_text = "A" * 500
    truncated, was_cut = truncate_input(long_text, 200)
    assert was_cut
    assert len(truncated) > 200
    assert "[TRUNCATED" in truncated


def test_extract_signatures():
    logs = (
        "2026-10-11 12:00:01 INFO Starting worker\n"
        "2026-10-11 12:00:02 FATAL: connection to database failed\n"
        "2026-10-11 12:00:03 psycopg2.OperationalError: server closed connection unexpectedly\n"
        "2026-10-11 12:00:04 HTTP 500 Internal Server Error\n"
    )
    signatures = extract_signatures(logs)
    assert len(signatures) >= 2
    assert any("FATAL" in s or "connection" in s for s in signatures)
    assert any("OperationalError" in s for s in signatures)


def test_format_untrusted_block():
    user_log = "Error in line 42; DROP TABLE users; Authorization: Bearer abcdef123456789012345"
    block = format_untrusted_block("Application Logs", user_log)
    assert "BEGIN UNTRUSTED APPLICATION LOGS" in block
    assert "END UNTRUSTED APPLICATION LOGS" in block
    assert "NOTE TO ASSISTANT" in block
    assert "[REDACTED_BEARER_TOKEN]" in block
