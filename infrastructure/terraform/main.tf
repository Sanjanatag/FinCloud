# ==============================================================================
# FinCloud — Cloud-Native Fintech Platform
# Main Terraform configuration
#
# Free-tier design constraints:
#   - 1x t2.micro EC2 instance (ECS cluster)
#   - 2 containers max (user-service + transaction-service)
#   - 1x db.t3.micro RDS PostgreSQL (20GB)
#   - 1x DynamoDB table (provisioned, 5 RCU/WCU)
#   - 1x SQS queue (≤10K messages/month)
#   - 1x Lambda function (≤100K invocations/month)
#   - 1x ALB
#   - 1x API Gateway
#   - 1x KMS key
#   - 1x Secrets Manager secret
#   - CloudWatch logs (7-day retention, ≤5GB)
# ==============================================================================

# All resources are defined in their respective .tf files:
#   - provider.tf   → AWS provider and backend
#   - variables.tf  → Input variables
#   - vpc.tf        → VPC, subnets, routing
#   - kms.tf        → Encryption key
#   - secrets.tf    → Secrets Manager
#   - ecr.tf        → Container registries
#   - iam.tf        → IAM roles and policies
#   - rds.tf        → PostgreSQL database
#   - dynamodb.tf   → Audit logs table
#   - sqs.tf        → Transaction event queue
#   - alb.tf        → Application Load Balancer
#   - ecs.tf        → ECS cluster, tasks, services
#   - lambda.tf     → Fraud detection function
#   - api_gateway.tf → Public API layer
#   - cloudwatch.tf → Logging, alarms, dashboard
#   - outputs.tf    → Output values
