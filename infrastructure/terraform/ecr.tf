# ==============================================================================
# ECR — Container registries (free tier: 500MB storage for 12 months)
# Two repositories for user-service and transaction-service
# ==============================================================================

resource "aws_ecr_repository" "user_service" {
  name                 = "${var.project_name}-user-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Name = "${var.project_name}-user-service" }
}

resource "aws_ecr_repository" "transaction_service" {
  name                 = "${var.project_name}-transaction-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Name = "${var.project_name}-transaction-service" }
}

# Lifecycle policy to keep only 3 images (minimize storage for free tier)
resource "aws_ecr_lifecycle_policy" "user_service" {
  repository = aws_ecr_repository.user_service.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only 3 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = { type = "expire" }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "transaction_service" {
  repository = aws_ecr_repository.transaction_service.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only 3 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = { type = "expire" }
      }
    ]
  })
}
