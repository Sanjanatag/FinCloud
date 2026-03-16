from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, hash_password, verify_password
from .database import get_db
from .models import User, Wallet
from .schemas import (
    HealthResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserWithWallet,
    WalletResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="healthy", service="user-service", version="1.0.0")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
    )
    db.add(user)
    db.flush()

    wallet = Wallet(user_id=user.id, balance=Decimal("1000.00"), currency="USD")
    db.add(wallet)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user_id=str(user.id))


@router.get("/me", response_model=UserWithWallet)
def get_profile(current_user: User = Depends(get_current_user)):
    return UserWithWallet(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        wallet=WalletResponse(
            id=current_user.wallet.id,
            balance=current_user.wallet.balance,
            currency=current_user.wallet.currency,
            is_frozen=current_user.wallet.is_frozen,
        ) if current_user.wallet else None,
    )


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
