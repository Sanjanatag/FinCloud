import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

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


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestHealthCheck:
    def test_health_endpoint(self):
        response = client.get("/api/v1/users/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "user-service"


class TestUserRegistration:
    def test_register_success(self):
        response = client.post(
            "/api/v1/users/register",
            json={
                "email": "test@example.com",
                "password": "securepassword123",
                "full_name": "Test User",
                "phone": "+1234567890",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "id" in data

    def test_register_duplicate_email(self):
        client.post(
            "/api/v1/users/register",
            json={
                "email": "duplicate@example.com",
                "password": "securepassword123",
                "full_name": "Dup User",
            },
        )
        response = client.post(
            "/api/v1/users/register",
            json={
                "email": "duplicate@example.com",
                "password": "securepassword123",
                "full_name": "Dup User 2",
            },
        )
        assert response.status_code == 409

    def test_register_invalid_email(self):
        response = client.post(
            "/api/v1/users/register",
            json={
                "email": "not-an-email",
                "password": "securepassword123",
                "full_name": "Bad Email User",
            },
        )
        assert response.status_code == 422

    def test_register_short_password(self):
        response = client.post(
            "/api/v1/users/register",
            json={
                "email": "short@example.com",
                "password": "short",
                "full_name": "Short Pass User",
            },
        )
        assert response.status_code == 422


class TestUserLogin:
    def test_login_success(self):
        client.post(
            "/api/v1/users/register",
            json={
                "email": "login@example.com",
                "password": "securepassword123",
                "full_name": "Login User",
            },
        )
        response = client.post(
            "/api/v1/users/login",
            json={"email": "login@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self):
        response = client.post(
            "/api/v1/users/login",
            json={"email": "login@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self):
        response = client.post(
            "/api/v1/users/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert response.status_code == 401


class TestUserProfile:
    def test_get_profile_unauthorized(self):
        response = client.get("/api/v1/users/me")
        assert response.status_code == 403

    def test_get_profile_success(self):
        client.post(
            "/api/v1/users/register",
            json={
                "email": "profile@example.com",
                "password": "securepassword123",
                "full_name": "Profile User",
            },
        )
        login_resp = client.post(
            "/api/v1/users/login",
            json={"email": "profile@example.com", "password": "securepassword123"},
        )
        token = login_resp.json()["access_token"]

        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profile@example.com"
