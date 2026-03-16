import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


def test_check_high_value_transfer():
    from services.fraud_service.lambda_function import check_high_value_transfer

    assert check_high_value_transfer(Decimal("100")) is None
    assert check_high_value_transfer(Decimal("4999")) is None

    result = check_high_value_transfer(Decimal("5000"))
    assert result is not None
    assert result["rule"] == "high_value_transfer"
    assert result["severity"] == "medium"

    result = check_high_value_transfer(Decimal("9000"))
    assert result is not None
    assert result["severity"] == "high"


def test_calculate_risk_score():
    from services.fraud_service.lambda_function import calculate_risk_score

    assert calculate_risk_score([]) == "low"
    assert calculate_risk_score([{"severity": "medium"}]) == "medium"
    assert calculate_risk_score([{"severity": "high"}]) == "high"
    assert calculate_risk_score([{"severity": "medium"}, {"severity": "high"}]) == "high"


@patch("services.fraud_service.lambda_function.write_audit_log")
def test_handler_clear_transaction(mock_audit):
    from services.fraud_service.lambda_function import handler

    event = {
        "Records": [
            {
                "body": json.dumps({
                    "transaction_id": "test-123",
                    "sender_id": "user-1",
                    "receiver_id": "user-2",
                    "amount": "100.00",
                    "currency": "USD",
                    "timestamp": "2025-01-01T00:00:00+00:00",
                }),
                "messageId": "msg-1",
            }
        ]
    }

    result = handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body) == 1
    assert body[0]["risk_score"] == "low"
    assert body[0]["status"] == "clear"
