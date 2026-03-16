"""
FinCloud Fraud Detection Lambda Function

Triggered by SQS messages containing transaction events.
Performs basic anomaly detection and writes audit logs to DynamoDB.

Free-tier constraints:
  - Lambda: ≤100K invocations/month (we expect ≤10K)
  - DynamoDB: ≤5GB storage, 25 RCU/WCU
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "fincloud_audit_logs")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
HIGH_VALUE_THRESHOLD = Decimal(os.environ.get("HIGH_VALUE_THRESHOLD", "5000"))
RAPID_TRANSFER_WINDOW_SECONDS = int(os.environ.get("RAPID_TRANSFER_WINDOW_SECONDS", "300"))

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


def check_high_value_transfer(amount: Decimal) -> dict | None:
    if amount >= HIGH_VALUE_THRESHOLD:
        return {
            "rule": "high_value_transfer",
            "severity": "medium" if amount < Decimal("8000") else "high",
            "message": f"High-value transfer detected: ${amount}",
        }
    return None


def check_rapid_transfers(sender_id: str, timestamp: str) -> dict | None:
    """Check if the sender has multiple recent transactions (basic frequency check)."""
    try:
        current_time = datetime.fromisoformat(timestamp)
        window_start = current_time.timestamp() - RAPID_TRANSFER_WINDOW_SECONDS

        response = table.query(
            IndexName="sender-timestamp-index",
            KeyConditionExpression="sender_id = :sid AND #ts > :window",
            ExpressionAttributeNames={"#ts": "timestamp"},
            ExpressionAttributeValues={
                ":sid": sender_id,
                ":window": str(window_start),
            },
            Limit=10,
        )

        recent_count = response.get("Count", 0)
        if recent_count >= 3:
            return {
                "rule": "rapid_transfers",
                "severity": "high",
                "message": f"Rapid transfers detected: {recent_count + 1} transactions in {RAPID_TRANSFER_WINDOW_SECONDS}s from sender {sender_id}",
            }
    except Exception as e:
        logger.warning(f"Rapid transfer check failed (non-critical): {e}")
    return None


def write_audit_log(transaction_data: dict, anomalies: list[dict], risk_score: str):
    try:
        table.put_item(Item={
            "id": str(uuid.uuid4()),
            "transaction_id": transaction_data["transaction_id"],
            "sender_id": transaction_data["sender_id"],
            "receiver_id": transaction_data["receiver_id"],
            "amount": transaction_data["amount"],
            "currency": transaction_data.get("currency", "USD"),
            "risk_score": risk_score,
            "anomalies": json.dumps(anomalies) if anomalies else "[]",
            "is_flagged": len(anomalies) > 0,
            "timestamp": transaction_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "ttl": int(time.time()) + (90 * 24 * 3600),  # 90-day retention
        })
        logger.info(f"Audit log written for transaction {transaction_data['transaction_id']}")
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
        raise


def calculate_risk_score(anomalies: list[dict]) -> str:
    if not anomalies:
        return "low"
    severities = [a.get("severity", "low") for a in anomalies]
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def handler(event, context):
    """SQS Lambda handler — processes transaction events for fraud detection."""
    logger.info(f"Processing {len(event.get('Records', []))} SQS messages")

    results = []
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            transaction_id = body.get("transaction_id", "unknown")
            amount = Decimal(body.get("amount", "0"))

            logger.info(f"Analyzing transaction {transaction_id}: amount={amount}")

            anomalies = []

            high_value_result = check_high_value_transfer(amount)
            if high_value_result:
                anomalies.append(high_value_result)

            rapid_result = check_rapid_transfers(body.get("sender_id", ""), body.get("timestamp", ""))
            if rapid_result:
                anomalies.append(rapid_result)

            risk_score = calculate_risk_score(anomalies)

            write_audit_log(body, anomalies, risk_score)

            result = {
                "transaction_id": transaction_id,
                "risk_score": risk_score,
                "anomalies_found": len(anomalies),
                "status": "flagged" if anomalies else "clear",
            }
            results.append(result)

            if anomalies:
                logger.warning(f"ANOMALY DETECTED for transaction {transaction_id}: {anomalies}")
            else:
                logger.info(f"Transaction {transaction_id} passed all checks")

        except Exception as e:
            logger.error(f"Error processing record: {e}")
            results.append({"error": str(e), "record": record.get("messageId", "unknown")})

    logger.info(f"Processed {len(results)} transactions")
    return {"statusCode": 200, "body": json.dumps(results, default=str)}
