"""
Модели SQLAlchemy для Банка Анисов.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "Captain" или "Passenger"
    balance = Column(Float, default=0.0)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("family_members.id"), nullable=False)
    amount = Column(Float, nullable=False)  # положительное = доход, отрицательное = расход
    type = Column(String, nullable=False)  # "earn", "spend", "transfer", "deposit"
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ShipTreasury(Base):
    __tablename__ = "ship_treasury"

    id = Column(Integer, primary_key=True, index=True)
    total_balance = Column(Float, default=0.0)
