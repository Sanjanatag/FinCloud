import json
import os
from functools import lru_cache

import boto3
from pydantic_settings import BaseSettings


def _load_secrets_manager() -> dict:
    """Load credentials from AWS Secrets Manager (1 secret for free tier)."""
    secret_name = os.getenv("AWS_SECRET_NAME")
    region = os.getenv("AWS_REGION", "us-east-1")
    if not secret_name:
        return {}
    try:
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except Exception:
        return {}


class Settings(BaseSettings):
    app_name: str = "FinCloud User Service"
    environment: str = "development"

    database_url: str = "postgresql://fincloud:fincloud@localhost:5432/fincloud"

    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    aws_region: str = "us-east-1"
    aws_secret_name: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    secrets = _load_secrets_manager()
    overrides = {}
    if "database_url" in secrets:
        overrides["database_url"] = secrets["database_url"]
    if "jwt_secret_key" in secrets:
        overrides["jwt_secret_key"] = secrets["jwt_secret_key"]
    return Settings(**overrides)
