import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from .models import Transaction, User, Wallet
from .schemas import (
    HealthResponse,
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    WalletResponse,
)
from .sqs import publish_transaction_event

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="healthy", service="transaction-service", version="1.0.0")


@router.post("/transfer", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if str(current_user.id) == str(payload.receiver_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot transfer to yourself")

    sender_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).with_for_update().first()
    if not sender_wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender wallet not found")
    if sender_wallet.is_frozen:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sender wallet is frozen")
    if sender_wallet.balance < payload.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

    receiver = db.query(User).filter(User.id == payload.receiver_id).first()
    if not receiver or not receiver.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receiver not found")

    receiver_wallet = db.query(Wallet).filter(Wallet.user_id == payload.receiver_id).with_for_update().first()
    if not receiver_wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receiver wallet not found")
    if receiver_wallet.is_frozen:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Receiver wallet is frozen")

    transaction = Transaction(
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        status="completed",
    )

    sender_wallet.balance = sender_wallet.balance - payload.amount
    receiver_wallet.balance = receiver_wallet.balance + payload.amount

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    publish_transaction_event({
        "id": transaction.id,
        "sender_id": transaction.sender_id,
        "receiver_id": transaction.receiver_id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "created_at": transaction.created_at.isoformat(),
    })

    logger.info(f"Transfer {transaction.id}: {current_user.id} -> {payload.receiver_id} amount={payload.amount}")
    return transaction


@router.get("/history", response_model=TransactionListResponse)
def get_transaction_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Transaction).filter(
        (Transaction.sender_id == current_user.id) | (Transaction.receiver_id == current_user.id)
    )
    total = query.count()
    transactions = (
        query.order_by(Transaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return TransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/wallet", response_model=WalletResponse)
def get_wallet(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return wallet
