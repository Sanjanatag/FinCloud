# FinCloud — Cloud-Native Fintech Platform

A production-style cloud-native fintech platform on AWS demonstrating infrastructure as code, microservices architecture, DevSecOps pipelines, secure transaction processing, monitoring, and AI-powered anomaly detection — all within **AWS free-tier limits**.

## Architecture

```
Client → API Gateway → ALB → ECS (User Service | Transaction Service) → RDS PostgreSQL
                                        ↓
                                  SQS → Lambda (Fraud Detection) → DynamoDB (Audit Logs)
                                        ↓
                                  CloudWatch → AI Anomaly Detector (OpenAI)
```

See [docs/architecture.md](docs/architecture.md) for the full architecture diagram and free-tier compliance matrix.

## Project Structure

```
├── services/
│   ├── user-service/          # User registration, login, profile (FastAPI)
│   ├── transaction-service/   # Money transfers, wallet, history (FastAPI)
│   └── fraud-service/         # Lambda-based anomaly detection
├── infrastructure/
│   ├── terraform/             # Complete AWS infrastructure as code
│   └── docker-compose.yml     # Local development environment
├── monitoring/
│   └── anomaly_detector.py    # AI-powered CloudWatch log analysis
├── scripts/
│   ├── db_init.sql            # Database schema
│   ├── seed_data.py           # Demo data seeder
│   └── load_test.py           # Performance testing
├── .github/
│   └── workflows/
│       └── deploy.yml         # CI/CD pipeline
└── docs/
    └── architecture.md        # System design documentation
```

## Services

### User Service (Port 8000)

| Endpoint                     | Method | Description              |
|------------------------------|--------|--------------------------|
| `/api/v1/users/health`       | GET    | Health check             |
| `/api/v1/users/register`     | POST   | Register new user        |
| `/api/v1/users/login`        | POST   | Login (returns JWT)      |
| `/api/v1/users/me`           | GET    | Get current user profile |
| `/api/v1/users/users/{id}`   | GET    | Get user by ID           |

### Transaction Service (Port 8001)

| Endpoint                            | Method | Description              |
|-------------------------------------|--------|--------------------------|
| `/api/v1/transactions/health`       | GET    | Health check             |
| `/api/v1/transactions/transfer`     | POST   | Send money               |
| `/api/v1/transactions/history`      | GET    | Transaction history      |
| `/api/v1/transactions/wallet`       | GET    | Get wallet balance       |

### Fraud Detection Service (Lambda)

Consumes SQS messages and performs:
- High-value transfer detection (≥$5,000)
- Rapid transfer frequency analysis
- Writes audit logs to DynamoDB

## Technology Stack

| Layer              | Technology                        |
|--------------------|-----------------------------------|
| Language           | Python 3.12                       |
| Framework          | FastAPI + Uvicorn                 |
| Database           | PostgreSQL 15 (RDS)               |
| NoSQL              | DynamoDB                          |
| Queue              | SQS                               |
| Compute            | ECS on EC2, Lambda                |
| IaC                | Terraform                         |
| Containers         | Docker                            |
| CI/CD              | GitHub Actions                    |
| Monitoring         | CloudWatch + OpenAI               |
| Security           | IAM, KMS, Secrets Manager, JWT    |

## Local Development

### Prerequisites

- Docker and Docker Compose
- Python 3.12+
- AWS CLI (for cloud deployment)
- Terraform 1.5+ (for infrastructure)

### Quick Start

```bash
# Start local services (PostgreSQL + LocalStack + microservices)
cd infrastructure
docker-compose up -d

# Or run services individually
cd services/user-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

cd services/transaction-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Seed Demo Data

```bash
python scripts/seed_data.py --base-url http://localhost:8000
```

### Run Tests

```bash
cd services/user-service && python -m pytest tests/ -v
cd services/transaction-service && python -m pytest tests/ -v
```

### Load Testing

```bash
python scripts/load_test.py --base-url http://localhost:8000 --requests 100
```

## AWS Deployment

### 1. Configure Terraform Backend

```bash
aws s3 mb s3://fincloud-terraform-state
aws dynamodb create-table \
  --table-name fincloud-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 2. Deploy Infrastructure

```bash
cd infrastructure/terraform
terraform init
terraform plan -var="db_password=YOUR_SECURE_PASSWORD"
terraform apply -var="db_password=YOUR_SECURE_PASSWORD"
```

### 3. Build and Push Images

```bash
aws ecr get-login-password | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# User Service
cd services/user-service
docker build -t fincloud-user-service .
docker tag fincloud-user-service:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/fincloud-user-service:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/fincloud-user-service:latest

# Transaction Service
cd services/transaction-service
docker build -t fincloud-transaction-service .
docker tag fincloud-transaction-service:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/fincloud-transaction-service:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/fincloud-transaction-service:latest
```

### 4. Run Anomaly Detection

```bash
# One-time analysis
python monitoring/anomaly_detector.py

# Scheduled (every 60 minutes)
python monitoring/anomaly_detector.py --schedule 60

# With OpenAI integration
OPENAI_API_KEY=sk-... python monitoring/anomaly_detector.py
```

## CI/CD Pipeline

The GitHub Actions pipeline runs on push to `main`:

1. **Test & Lint** — Unit tests and ruff linting for both services
2. **Security Scan** — Bandit SAST + dependency vulnerability checks
3. **Build & Push** — Docker build, Trivy scan, push to ECR
4. **Terraform** — Infrastructure plan and apply
5. **ECS Deploy** — Force new deployment, wait for stabilization
6. **Post-Deploy** — Health checks and alarm verification

## Free-Tier Compliance

Every design decision prioritizes staying within AWS free-tier limits:

| Constraint               | Limit           | Implementation                          |
|--------------------------|-----------------|----------------------------------------|
| EC2 instances            | 1x t2.micro     | Single ECS cluster instance            |
| Containers               | 2 max           | user-service + transaction-service     |
| Container resources      | 256 CPU / 256MB | Hard limits in task definitions        |
| RDS                      | db.t3.micro     | 20GB, no multi-AZ, 1-day backups      |
| DynamoDB                 | ≤5GB            | TTL auto-deletes records after 90 days |
| SQS                      | ≤10K msg/month  | Batch processing, long polling         |
| Lambda                   | ≤100K/month     | SQS batch size 10, 60s batching window |
| CloudWatch               | ≤5GB logs       | 7-day retention on all log groups      |
| Secrets Manager          | 1 secret        | All credentials in single JSON blob    |
| KMS                      | 1 key           | Single CMK for all encryption          |
| ECR                      | ≤500MB          | Lifecycle policy keeps max 3 images    |
| API Gateway              | ≤5K calls/month | Throttle: 5 req/sec, burst 10         |

## Security

- **Authentication**: JWT tokens with bcrypt password hashing
- **Encryption**: KMS-managed encryption for RDS, SQS, DynamoDB, Secrets Manager
- **IAM**: Least-privilege roles for every service
- **Network**: Private subnets for RDS, security groups per service
- **Scanning**: Trivy container scanning, Bandit SAST, dependency auditing
- **Secrets**: No hardcoded credentials; Secrets Manager for all sensitive values
