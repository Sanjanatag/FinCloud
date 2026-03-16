output "api_gateway_url" {
  description = "Public API Gateway URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "sqs_queue_url" {
  description = "SQS transaction queue URL"
  value       = aws_sqs_queue.transactions.url
}

output "dynamodb_table_name" {
  description = "DynamoDB audit logs table name"
  value       = aws_dynamodb_table.audit_logs.name
}

output "ecr_user_service_url" {
  description = "ECR repository URL for user service"
  value       = aws_ecr_repository.user_service.repository_url
}

output "ecr_transaction_service_url" {
  description = "ECR repository URL for transaction service"
  value       = aws_ecr_repository.transaction_service.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "lambda_function_name" {
  description = "Lambda fraud detection function name"
  value       = aws_lambda_function.fraud_detection.function_name
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "kms_key_id" {
  description = "KMS encryption key ID"
  value       = aws_kms_key.main.key_id
}

output "secret_arn" {
  description = "Secrets Manager secret ARN"
  value       = aws_secretsmanager_secret.app_credentials.arn
  sensitive   = true
}
