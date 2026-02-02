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
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)

    # Relationship to Asset
    asset = relationship("Asset", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, amount={self.amount}, category='{self.category}')>"

# Asset tracking (Savings, Funds, Investments, etc.)
class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # e.g., Alipay, ICBC, Fund 001
    category = Column(String) # SAVINGS, FUND, FIXED_TERM, STOCK, CRYPTO, OTHERS
    type = Column(String, default="LIQUID") # LIQUID, CREDIT, INVESTMENT, OTHER
    balance = Column(Float, default=0.0)
    credit_limit = Column(Float, nullable=True) # For Credit Cards
    billing_day = Column(Integer, nullable=True) # For Credit Cards
    currency = Column(String, default="CNY")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to Transactions
    transactions = relationship("Transaction", back_populates="asset")

    def __repr__(self):
        return f"<Asset(name='{self.name}', balance={self.balance}, type='{self.type}')>"

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, unique=True, index=True)
    limit_amount = Column(Float, nullable=False)
    currency = Column(String, default="CNY")
    alert_threshold = Column(Float, default=0.8) # Alert when 80% reached
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Budget(category='{self.category}', limit={self.limit_amount})>"
