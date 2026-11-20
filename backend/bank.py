from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from database import get_db
import models

router = APIRouter()

class TransactionCreate(BaseModel):
    user_id: int
    amount: float
    type: str
    description: str
    category: str = "Общее"

class TransferRequest(BaseModel):
    from_user_id: int
    to_user_id: int
    amount: float

class FamilyMemberResponse(BaseModel):
    id: int
    name: str
    role: str
    balance: float
    class Config:
        from_attributes = True

@router.get("/family", response_model=List[FamilyMemberResponse])
def get_family(db: Session = Depends(get_db)):
    return db.query(models.FamilyMember).order_by(models.FamilyMember.role.desc()).all()

@router.get("/treasury")
def get_treasury(db: Session = Depends(get_db)):
    treasury = db.query(models.ShipTreasury).first()
    return {"total_balance": treasury.total_balance if treasury else 0.0}

@router.post("/transaction")
def create_transaction(tx: TransactionCreate, db: Session = Depends(get_db)):
    user = db.query(models.FamilyMember).filter(models.FamilyMember.id == tx.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.balance += tx.amount
    treasury = db.query(models.ShipTreasury).first()
    if treasury:
        treasury.total_balance += tx.amount
    new_tx = models.Transaction(user_id=tx.user_id, amount=tx.amount, type=tx.type, description=tx.description, category=tx.category)
    db.add(new_tx)
    db.commit()
    return {"status": "ok", "new_balance": user.balance}
