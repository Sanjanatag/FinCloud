# FinCloud - Cloud-Native Fintech Platform Architecture

## System Overview

FinCloud is a production-style cloud-native fintech platform built on AWS that demonstrates
infrastructure as code, microservices architecture, DevSecOps pipelines, secure transaction
processing, monitoring, and AI-powered anomaly detection — all within AWS free-tier limits.

## Architecture Diagram

```
                    ┌─────────────────┐
                    │   GitHub Actions │
                    │   CI/CD Pipeline │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │      ECR        │
                    │ Container Images│
                    └────────┬────────┘
                             │
┌────────────────────────────▼──────────────────────────────────┐
│                         AWS VPC                                │
│                                                                │
│  ┌──────────────┐    ┌──────────────────────────────────────┐ │
│  │ API Gateway   │───▶│  Application Load Balancer            │ │
│  │ (Public API)  │    │  (Path-based routing)                 │ │
│  └──────────────┘    └──────────┬───────────┬───────────────┘ │
│                                 │           │                  │
│                    ┌────────────▼──┐  ┌─────▼──────────────┐  │
│                    │  ECS Cluster   │  │                    │  │
│                    │  (t2.micro)    │  │                    │  │
│                    │                │  │                    │  │
│                    │ ┌────────────┐ │  │                    │  │
│                    │ │   User     │ │  │                    │  │
│                    │ │  Service   │ │  │   Transaction      │  │
│                    │ │ (256MB)    │ │  │   Service           │  │
│                    │ └─────┬──────┘ │  │   (256MB)           │  │
│                    │       │        │  │                    │  │
│                    └───────┼────────┘  └──────┬─────────────┘ │
│                            │                  │                │
│                    ┌───────▼──────────────────▼──────┐        │
│                    │      RDS PostgreSQL              │        │
│                    │      (db.t3.micro, 20GB)         │        │
│                    │                                  │        │
│                    │  ┌────────┬──────────┬────────┐  │        │
│                    │  │ users  │ wallets  │ txns   │  │        │
│                    │  └────────┴──────────┴────────┘  │        │
│                    └─────────────────────────────────┘        │
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐ │
│  │   SQS Queue   │───▶│    Lambda     │───▶│    DynamoDB       │ │
│  │  (txn events) │    │ (Fraud Check) │    │  (audit_logs)     │ │
│  └──────────────┘    └──────┬───────┘    └──────────────────┘ │
│                             │                                  │
│                    ┌────────▼────────┐                         │
│                    │   CloudWatch     │                         │
│                    │   (Logs/Metrics) │                         │
│                    └────────┬────────┘                         │
│                             │                                  │
│  ┌──────────────────────────▼──────────────────────────────┐  │
│  │  Monitoring Script (Scheduled) → OpenAI Anomaly Detection│  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ KMS (1 key)  │  │Secrets Mgr   │  │  IAM (least-priv)    │ │
│  │              │  │ (1 secret)   │  │                      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

## Free-Tier Compliance Matrix

| AWS Service       | Free Tier Limit              | Our Usage                    | Status |
|-------------------|------------------------------|------------------------------|--------|
| EC2 (t2.micro)    | 750 hrs/month                | 1 instance, ~720 hrs/month   | ✅     |
| ECS               | No additional charge         | Runs on EC2                  | ✅     |
| RDS (db.t3.micro) | 750 hrs/month, 20GB          | 1 instance, ≤20GB            | ✅     |
| DynamoDB          | 25GB, 25 RCU/WCU            | ≤5GB, low R/W                | ✅     |
| SQS               | 1M requests/month            | ≤10K messages/month          | ✅     |
| Lambda            | 1M invocations/month         | ≤100K invocations/month      | ✅     |
| API Gateway       | 1M calls/month (12 months)   | ≤5K calls/month              | ✅     |
| CloudWatch        | 5GB logs ingestion           | ≤5GB logs                    | ✅     |
| ECR               | 500MB storage (12 months)    | 2 images ~200MB              | ✅     |
| Secrets Manager   | 30-day free trial            | 1 secret                     | ✅     |
| KMS               | 20K free requests/month      | 1 key, minimal requests      | ✅     |
| ALB               | 750 hrs/month (12 months)    | 1 ALB                        | ✅     |

## Security Design

- **IAM**: Least-privilege roles for ECS tasks, Lambda, and CI/CD
- **KMS**: Single CMK encrypts RDS, SQS, and DynamoDB
- **Secrets Manager**: Single secret stores all database credentials as JSON
- **VPC**: Private subnets for RDS, public subnets for ALB
- **Security Groups**: Strict ingress/egress rules per service
- **JWT**: Token-based authentication for API endpoints

## Data Flow

1. Client → API Gateway → ALB → User/Transaction Service
2. Transaction Service → SQS (async event)
3. SQS → Lambda (fraud detection)
4. Lambda → DynamoDB (audit log)
5. CloudWatch ← All services (logs/metrics)
6. Monitoring Script → CloudWatch → OpenAI (anomaly analysis)
