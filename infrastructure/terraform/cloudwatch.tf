# ==============================================================================
# CloudWatch — Logging and monitoring (free tier: 5GB log ingestion)
# Short retention periods to minimize storage costs
# ==============================================================================

# ---------- Log Groups ----------

resource "aws_cloudwatch_log_group" "user_service" {
  name              = "/ecs/${var.project_name}/user-service"
  retention_in_days = 7

  tags = { Name = "${var.project_name}-user-service-logs" }
}

resource "aws_cloudwatch_log_group" "transaction_service" {
  name              = "/ecs/${var.project_name}/transaction-service"
  retention_in_days = 7

  tags = { Name = "${var.project_name}-transaction-service-logs" }
}

resource "aws_cloudwatch_log_group" "fraud_detection" {
  name              = "/aws/lambda/${var.project_name}-fraud-detection"
  retention_in_days = 7

  tags = { Name = "${var.project_name}-fraud-detection-logs" }
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/api-gateway/${var.project_name}"
  retention_in_days = 7

  tags = { Name = "${var.project_name}-api-gateway-logs" }
}

# ---------- Metric Alarms ----------

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "${var.project_name}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Triggers when 5XX errors exceed 10 in 5 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = { Name = "${var.project_name}-error-rate-alarm" }
}

resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "${var.project_name}-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Average"
  threshold           = 0.2 # 200ms SLA target
  alarm_description   = "Triggers when average latency exceeds 200ms"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = { Name = "${var.project_name}-latency-alarm" }
}

resource "aws_cloudwatch_metric_alarm" "sqs_queue_depth" {
  alarm_name          = "${var.project_name}-sqs-queue-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = 100
  alarm_description   = "Triggers when SQS queue depth exceeds 100"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.transactions.name
  }

  tags = { Name = "${var.project_name}-sqs-depth-alarm" }
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.project_name}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Triggers when RDS CPU exceeds 80%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  tags = { Name = "${var.project_name}-rds-cpu-alarm" }
}

# ---------- Dashboard ----------

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.main.arn_suffix],
            ["AWS/ApplicationELB", "HTTPCode_Target_2XX_Count", "LoadBalancer", aws_lb.main.arn_suffix],
            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", aws_lb.main.arn_suffix],
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "ALB Request Metrics"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", aws_lb.main.arn_suffix],
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Response Latency"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", aws_db_instance.main.identifier],
            ["AWS/RDS", "FreeStorageSpace", "DBInstanceIdentifier", aws_db_instance.main.identifier],
            ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", aws_db_instance.main.identifier],
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "RDS Metrics"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/SQS", "NumberOfMessagesSent", "QueueName", aws_sqs_queue.transactions.name],
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.transactions.name],
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "SQS Metrics"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.project_name}-fraud-detection"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.project_name}-fraud-detection"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-fraud-detection"],
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Lambda Fraud Detection Metrics"
        }
      }
    ]
  })
}
