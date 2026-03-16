# ==============================================================================
# RDS PostgreSQL — free tier: db.t3.micro, 20GB, 750 hrs/month (12 months)
# Single instance, no multi-AZ (cost optimization)
# ==============================================================================

resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-rds-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  ingress {
    description     = "PostgreSQL from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-rds-sg" }
}

resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "15.4"

  instance_class        = var.rds_instance_class
  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_allocated_storage # No autoscaling — stay within free tier

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  storage_encrypted = true
  kms_key_id        = aws_kms_key.main.arn

  backup_retention_period = 1 # Minimal backups for free tier
  skip_final_snapshot     = true
  deletion_protection     = false

  multi_az               = false # Single AZ for free tier
  publicly_accessible    = false
  storage_type           = "gp2"
  copy_tags_to_snapshot  = true

  performance_insights_enabled = false # Not available on free tier

  tags = { Name = "${var.project_name}-db" }
}
