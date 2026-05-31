from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.models.statement import BankStatement, StatementTransaction
from app.services.document_parser import statement_parser
from app.services.finlens_engine import finlens_engine
from app.api.v1.auth import RoleEnforcer
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finlens", tags=["FinLens"])

# 1. Schemas for Statement Uploads
class DocumentUploadRequest(BaseModel):
    raw_text: str = Field(
        ...,
        min_length=10,
        max_length=500_000,  # 500KB max — a 1000-page statement is ~200KB text
        description="Raw text extracted from the financial document"
    )

class DocumentUploadResponse(BaseModel):
    statement_id: int
    bank_name: str
    account_number: str
    total_deposits: float
    total_withdrawals: float
    ending_balance: float
    transaction_count: int
    status: str

# 2. Schemas for Queries
class DocumentQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language query about numerical/textual values")
    statement_id: int = Field(..., description="ID of the target parsed statement")

class DocumentQueryResponse(BaseModel):
    answer: str
    numerical_value: float
    compiled_sql: str
    audit_status: str

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    payload: DocumentUploadRequest, 
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(RoleEnforcer("analyst"))
):
    """Ingests a text-based bank statement, parses tables/metadata, and commits to databases with ownership mapping."""
    try:
        result = statement_parser.parse_and_store_statement(
            db, payload.raw_text, owner_username=current_user["username"]
        )
        return DocumentUploadResponse(
            statement_id=result["statement_id"],
            bank_name=result["bank_name"],
            account_number=result["account_number"],
            total_deposits=result["total_deposits"],
            total_withdrawals=result["total_withdrawals"],
            ending_balance=result["ending_balance"],
            transaction_count=result["transaction_count"],
            status="ingested_and_committed"
        )
    except Exception as e:
        logger.error(f"Document upload and parsing pipeline failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Financial statement parsing failed: {str(e)}"
        )

@router.post("/query", response_model=DocumentQueryResponse, status_code=status.HTTP_200_OK)
async def query_document(
    payload: DocumentQueryRequest, 
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(RoleEnforcer("analyst"))
):
    """Intercepts numerical questions and translates them into precise SQL to prevent hallucinations."""
    try:
        # Enforce ownership check before executing query
        statement = db.query(BankStatement).filter(
            BankStatement.id == payload.statement_id,
            BankStatement.owner_username == current_user["username"]
        ).first()
        if not statement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Statement ID {payload.statement_id} not found."
            )
            
        result = finlens_engine.answer_numerical_query(
            db, payload.query, payload.statement_id, username=current_user["username"]
        )
        return DocumentQueryResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query statement ID {payload.statement_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Statement query execution failed: {str(e)}"
        )

@router.get("/statements/{id}", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
def get_statement_details(
    id: int, 
    db: Session = Depends(get_db), 
    current_user: Dict[str, Any] = Depends(RoleEnforcer("analyst"))
):
    """Retrieves basic metadata and transactional transaction counts for a bank statement with ownership checks."""
    statement = db.query(BankStatement).filter(
        BankStatement.id == id,
        BankStatement.owner_username == current_user["username"]
    ).first()
    if not statement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Statement ID {id} not found.")
        
    transaction_count = db.query(StatementTransaction).filter(StatementTransaction.statement_id == id).count()
    
    return {
        "statement_id": statement.id,
        "bank_name": statement.bank_name,
        "account_number": statement.account_number,
        "period": statement.statement_period,
        "total_deposits": statement.total_deposits,
        "total_withdrawals": statement.total_withdrawals,
        "ending_balance": statement.ending_balance,
        "transaction_count": transaction_count
    }

@router.get("/statements/{id}/summary", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
def get_statement_summary(
    id: int, 
    db: Session = Depends(get_db), 
    current_user: Dict[str, Any] = Depends(RoleEnforcer("analyst"))
):
    """Generates an automated summary of a bank statement including monthly debits vs credits, and top transaction descriptions with ownership checks."""
    try:
        statement = db.query(BankStatement).filter(
            BankStatement.id == id,
            BankStatement.owner_username == current_user["username"]
        ).first()
        if not statement:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Statement ID {id} not found.")
            
        total_credits = statement.total_deposits
        total_debits = statement.total_withdrawals
        ratio = total_credits / total_debits if total_debits > 0 else total_credits
        
        top_debits = db.query(StatementTransaction).filter(
            StatementTransaction.statement_id == id,
            StatementTransaction.transaction_type == "DEBIT"
        ).order_by(StatementTransaction.amount.desc()).limit(5).all()
        
        top_categories = []
        for tx in top_debits:
            top_categories.append({
                "description": tx.description,
                "amount": tx.amount,
                "date": tx.date
            })
            
        credit_count = db.query(StatementTransaction).filter(
            StatementTransaction.statement_id == id,
            StatementTransaction.transaction_type == "CREDIT"
        ).count()
        
        debit_count = db.query(StatementTransaction).filter(
            StatementTransaction.statement_id == id,
            StatementTransaction.transaction_type == "DEBIT"
        ).count()
        
        return {
            "statement_id": id,
            "bank_name": statement.bank_name,
            "account_number": statement.account_number,
            "period": statement.statement_period,
            "total_income": total_credits,
            "total_expense": total_debits,
            "income_to_expense_ratio": round(ratio, 2),
            "ending_balance": statement.ending_balance,
            "metrics": {
                "deposits_count": credit_count,
                "withdrawals_count": debit_count,
            },
            "top_expenditures": top_categories
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate statement summary for ID {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Statement summary generation failed: {str(e)}"
        )
