# ==============================================================================
# KMS — Single encryption key (free tier: 20K requests/month free)
# One key encrypts RDS, SQS, DynamoDB, and Secrets Manager
# ==============================================================================

resource "aws_kms_key" "main" {
  description             = "FinCloud master encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowRootAccount"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowServiceEncryption"
        Effect = "Allow"
        Principal = {
          Service = [
            "rds.amazonaws.com",
            "sqs.amazonaws.com",
            "dynamodb.amazonaws.com",
            "secretsmanager.amazonaws.com",
            "logs.amazonaws.com",
          ]
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey*",
          "kms:DescribeKey",
        ]
        Resource = "*"
      }
    ]
  })

  tags = { Name = "${var.project_name}-kms-key" }
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.project_name}-key"
  target_key_id = aws_kms_key.main.key_id
}

data "aws_caller_identity" "current" {}
