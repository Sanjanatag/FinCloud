variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "fincloud"
}

# VPC
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones (2 minimum for ALB)"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# EC2 / ECS — free tier: t2.micro, 750 hrs/month
variable "ec2_instance_type" {
  description = "EC2 instance type for ECS cluster (free tier: t2.micro)"
  type        = string
  default     = "t2.micro"
}

# RDS — free tier: db.t3.micro, 20GB, 750 hrs/month
variable "rds_instance_class" {
  description = "RDS instance class (free tier: db.t3.micro)"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "RDS storage in GB (free tier: ≤20GB)"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "fincloud"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "fincloud"
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

# Container resource limits — free tier constraints
variable "container_cpu" {
  description = "CPU units per container (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "container_memory" {
  description = "Memory per container in MB (free tier: ≤256MB)"
  type        = number
  default     = 256
}
