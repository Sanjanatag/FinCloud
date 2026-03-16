# ==============================================================================
# Secrets Manager — Single secret (free tier: 30-day trial, then $0.40/secret/month)
# Stores all credentials as a single JSON blob to minimize cost
# ==============================================================================

resource "aws_secretsmanager_secret" "app_credentials" {
  name       = "${var.project_name}-credentials"
  kms_key_id = aws_kms_key.main.arn

  tags = { Name = "${var.project_name}-credentials" }
}

resource "aws_secretsmanager_secret_version" "app_credentials" {
  secret_id = aws_secretsmanager_secret.app_credentials.id
  secret_string = jsonencode({
    database_url   = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.main.endpoint}/${var.db_name}"
    db_host        = aws_db_instance.main.address
    db_port        = tostring(aws_db_instance.main.port)
    db_name        = var.db_name
    db_username    = var.db_username
    db_password    = var.db_password
    jwt_secret_key = random_password.jwt_secret.result
  })
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}
