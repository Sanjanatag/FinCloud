# ==============================================================================
# SQS — Transaction event queue (free tier: 1M requests/month)
# Standard queue with dead-letter queue for failed messages
# Target: ≤10K messages/month
# ==============================================================================

resource "aws_sqs_queue" "transactions" {
  name                       = "${var.project_name}-transactions"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling to reduce API calls
  max_message_size           = 262144

  kms_master_key_id = aws_kms_key.main.id

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.transactions_dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Name = "${var.project_name}-transactions-queue" }
}

resource "aws_sqs_queue" "transactions_dlq" {
  name                      = "${var.project_name}-transactions-dlq"
  message_retention_seconds = 1209600 # 14 days

  kms_master_key_id = aws_kms_key.main.id

  tags = { Name = "${var.project_name}-transactions-dlq" }
}
