import json
import logging

import boto3
from botocore.exceptions import ClientError

from .config import get_settings

logger = logging.getLogger(__name__)


def publish_transaction_event(transaction_data: dict) -> bool:
    """Publish a transaction event to SQS for async fraud detection processing.

    SQS free tier: 1M requests/month. We target ≤10K messages/month.
    """
    settings = get_settings()
    if not settings.sqs_queue_url:
        logger.warning("SQS_QUEUE_URL not configured — skipping event publish")
        return False

    try:
        client = boto3.client("sqs", region_name=settings.aws_region)
        message_body = json.dumps({
            "event_type": "transaction_created",
            "transaction_id": str(transaction_data["id"]),
            "sender_id": str(transaction_data["sender_id"]),
            "receiver_id": str(transaction_data["receiver_id"]),
            "amount": str(transaction_data["amount"]),
            "currency": transaction_data["currency"],
            "timestamp": transaction_data["created_at"],
        })

        client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=message_body,
            MessageGroupId="transactions" if ".fifo" in settings.sqs_queue_url else None,
        ) if ".fifo" in settings.sqs_queue_url else client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=message_body,
        )

        logger.info(f"Published transaction event for {transaction_data['id']}")
        return True
    except ClientError as e:
        logger.error(f"Failed to publish to SQS: {e}")
        return False
