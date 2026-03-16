# ==============================================================================
# DynamoDB — Audit logs table (free tier: 25GB, 25 RCU/WCU)
# On-demand would exceed free tier; use provisioned with minimal capacity
# ==============================================================================

resource "aws_dynamodb_table" "audit_logs" {
  name         = "${var.project_name}_audit_logs"
  billing_mode = "PROVISIONED"

  read_capacity  = 5
  write_capacity = 5

  hash_key  = "id"
  range_key = "transaction_id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "transaction_id"
    type = "S"
  }

  attribute {
    name = "sender_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  # GSI for querying by sender (used by fraud detection)
  global_secondary_index {
    name            = "sender-timestamp-index"
    hash_key        = "sender_id"
    range_key       = "timestamp"
    projection_type = "ALL"
    read_capacity   = 5
    write_capacity  = 5
  }

  # TTL to auto-delete old records (keeps storage within free tier)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.main.arn
  }

  point_in_time_recovery {
    enabled = false # Disable to stay within free tier
  }

  tags = { Name = "${var.project_name}-audit-logs" }
}
