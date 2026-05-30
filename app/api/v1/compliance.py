from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from app.services.compliance_agent import compliance_agent
from app.api.v1.auth import RoleEnforcer
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["RegGuard"])

# 1. Schemas for Compliance Audits
class ComplianceCheckRequest(BaseModel):
    amount: float = Field(..., gt=0.0, description="Amount of the transaction in ₹ (INR)")
    channel: str = Field(..., description="Transaction processing channel (e.g., UPI, CASH, CARD, LRS)")
    is_international: bool = Field(False, description="Flag representing whether this is a cross-border transfer")
    user_id: uuid.UUID = Field(..., description="Cardholder's unique identification key")

class CitationDetail(BaseModel):
    document: str
    section: str
    clause: Optional[str] = None

class ComplianceCheckResponse(BaseModel):
    is_compliant: bool
    verdict: str
    violations: List[str]
    citations: List[CitationDetail]

# 2. Schemas for Compliance RAG Queries
class RegulationQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language regulation query")

class CitationQueryDetail(BaseModel):
    document: str
    section: str
    relevance_score: float

class RegulationQueryResponse(BaseModel):
    answer: str
    citations: List[CitationQueryDetail]

@router.post("/check", response_model=ComplianceCheckResponse, status_code=status.HTTP_200_OK)
async def check_compliance(
    payload: ComplianceCheckRequest,
    current_user: Dict[str, Any] = Depends(RoleEnforcer("readonly"))
):
    """Audits transaction limits against RBI, FEMA LRS, and PMLA reporting thresholds."""
    try:
        tx_dict = payload.model_dump()
        tx_dict["user_id"] = str(tx_dict["user_id"])
        
        # Invoke global compliance agent sweeps
        result = compliance_agent.check_transaction_compliance(tx_dict)
        return ComplianceCheckResponse(**result)
    except Exception as e:
        logger.error(f"Failed to check compliance for user {payload.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance check execution failed: {str(e)}"
        )

@router.post("/query", response_model=RegulationQueryResponse, status_code=status.HTTP_200_OK)
async def query_regulations(
    payload: RegulationQueryRequest,
    current_user: Dict[str, Any] = Depends(RoleEnforcer("readonly"))
):
    """Retrieves relevant circulars and generates cited compliance guidelines in real time."""
    try:
        result = compliance_agent.query_regulations(payload.query, username=current_user["username"])
        return RegulationQueryResponse(**result)
    except Exception as e:
        logger.error(f"Failed to query compliance regulations for query '{payload.query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance RAG execution failed: {str(e)}"
        )

