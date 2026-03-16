# ==============================================================================
# Lambda — Fraud detection worker (free tier: 1M invocations, 400K GB-sec/month)
# Triggered by SQS; target ≤100K invocations/month
# ==============================================================================

resource "aws_security_group" "lambda" {
  name_prefix = "${var.project_name}-lambda-"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-lambda-sg" }
}

data "archive_file" "fraud_service" {
  type        = "zip"
  source_file = "${path.module}/../../services/fraud-service/lambda_function.py"
  output_path = "${path.module}/lambda/fraud_service.zip"
}

resource "aws_lambda_function" "fraud_detection" {
  function_name = "${var.project_name}-fraud-detection"
  description   = "Fraud detection worker consuming transaction events from SQS"

  filename         = data.archive_file.fraud_service.output_path
  source_code_hash = data.archive_file.fraud_service.output_base64sha256
  handler          = "lambda_function.handler"
  runtime          = "python3.12"

  role    = aws_iam_role.lambda_execution.arn
  timeout = 30
  memory_size = 128 # Minimal memory for cost optimization

  environment {
    variables = {
      DYNAMODB_TABLE               = aws_dynamodb_table.audit_logs.name
      AWS_REGION_NAME              = var.aws_region
      HIGH_VALUE_THRESHOLD         = "5000"
      RAPID_TRANSFER_WINDOW_SECONDS = "300"
    }
  }

  kms_key_arn = aws_kms_key.main.arn

  tags = { Name = "${var.project_name}-fraud-detection" }
}

# SQS trigger — Lambda polls SQS for new messages
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.transactions.arn
  function_name    = aws_lambda_function.fraud_detection.arn
  batch_size       = 10
  enabled          = true

  # Process messages in small batches to stay within free tier
  maximum_batching_window_in_seconds = 60
}

resource "aws_lambda_permission" "sqs" {
  statement_id  = "AllowSQSInvocation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fraud_detection.function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = aws_sqs_queue.transactions.arn
}
