from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.document_parser import statement_parser
from app.services.finlens_engine import finlens_engine
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/docs", tags=["FinLens"])

# 1. Schemas for Statement Uploads
class DocumentUploadRequest(BaseModel):
    raw_text: str = Field(..., description="Raw text extracted from the financial document")

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
async def upload_document(payload: DocumentUploadRequest, db: Session = Depends(get_db)):
    """Ingests a text-based bank statement, parses tables/metadata, and commits to databases."""
    try:
        result = statement_parser.parse_and_store_statement(db, payload.raw_text)
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
async def query_document(payload: DocumentQueryRequest, db: Session = Depends(get_db)):
    """Intercepts numerical questions and translates them into precise SQL to prevent hallucinations."""
    try:
        result = finlens_engine.answer_numerical_query(db, payload.query, payload.statement_id)
        return DocumentQueryResponse(**result)
    except Exception as e:
        logger.error(f"Failed to query statement ID {payload.statement_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Statement query execution failed: {str(e)}"
        )
