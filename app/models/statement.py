from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base, engine

class BankStatement(Base):
    __tablename__ = "bank_statements"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    owner_username = Column(String(100), nullable=False, index=True)
    account_number = Column(String(50), nullable=False)
    bank_name = Column(String(100), nullable=False)
    total_deposits = Column(Float, default=0.0)
    total_withdrawals = Column(Float, default=0.0)
    ending_balance = Column(Float, default=0.0)
    statement_period = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    transactions = relationship("StatementTransaction", back_populates="statement", cascade="all, delete-orphan")

class StatementTransaction(Base):
    __tablename__ = "statement_transactions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    statement_id = Column(Integer, ForeignKey("bank_statements.id", ondelete="CASCADE"), nullable=False)
    date = Column(String(10), nullable=False) # Format: YYYY-MM-DD
    description = Column(String(255), nullable=False)
    transaction_type = Column(String(10), nullable=False) # CREDIT or DEBIT
    amount = Column(Float, nullable=False)
    balance = Column(Float, nullable=False)
    
    statement = relationship("BankStatement", back_populates="transactions")

# Create tables in database engine
Base.metadata.create_all(bind=engine)
