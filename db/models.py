from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="CNY")
    description = Column(String)
    category = Column(String) # e.g., Food, Transport, Salary
    type = Column(String) # INCOME, EXPENSE, INVEST_IN, INVEST_OUT
    raw_text = Column(Text) # The original message from user

    def __repr__(self):
        return f"<Transaction(id={self.id}, amount={self.amount}, category='{self.category}')>"

# Simple Asset tracking for now (e.g., "AAPL", "BTC")
class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True) # AAPL, BTC
    name = Column(String)
    quantity = Column(Float, default=0.0)
    average_cost = Column(Float, default=0.0) # Simple average cost basis
    
    def __repr__(self):
        return f"<Asset(symbol='{self.symbol}', quantity={self.quantity})>"
