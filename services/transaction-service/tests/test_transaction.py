from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, Wallet
from app.auth import get_current_user

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_txn.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


import uuid

SENDER_ID = uuid.uuid4()
RECEIVER_ID = uuid.uuid4()


def seed_test_data():
    db = TestingSessionLocal()
    if not db.query(User).first():
        sender = User(id=SENDER_ID, email="sender@test.com", password_hash="x", full_name="Sender")
        receiver = User(id=RECEIVER_ID, email="receiver@test.com", password_hash="x", full_name="Receiver")
        db.add_all([sender, receiver])
        db.flush()
        db.add(Wallet(user_id=SENDER_ID, balance=Decimal("1000.00")))
        db.add(Wallet(user_id=RECEIVER_ID, balance=Decimal("500.00")))
        db.commit()
    db.close()


seed_test_data()


def mock_current_user():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == SENDER_ID).first()
    db.close()
    return user


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = mock_current_user

client = TestClient(app)


class TestHealthCheck:
    def test_health(self):
        response = client.get("/api/v1/transactions/health")
        assert response.status_code == 200
        assert response.json()["service"] == "transaction-service"


class TestTransfer:
    @patch("app.routes.publish_transaction_event", return_value=True)
    def test_transfer_success(self, mock_sqs):
        response = client.post(
            "/api/v1/transactions/transfer",
            json={"receiver_id": str(RECEIVER_ID), "amount": 100.00, "description": "Test transfer"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "completed"
        assert Decimal(data["amount"]) == Decimal("100.00")

    @patch("app.routes.publish_transaction_event", return_value=True)
    def test_transfer_self_reject(self, mock_sqs):
        response = client.post(
            "/api/v1/transactions/transfer",
            json={"receiver_id": str(SENDER_ID), "amount": 50.00},
        )
        assert response.status_code == 400


class TestWallet:
    def test_get_wallet(self):
        response = client.get("/api/v1/transactions/wallet")
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert data["currency"] == "USD"


class TestHistory:
    def test_get_history(self):
        response = client.get("/api/v1/transactions/history")
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "total" in data
