"""Main FastAPI application for Synm Mediator."""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, Field
import yaml

from app.auth.pat import verify_pat
from app.store.sql import SQLStore
from app.store.vector import VectorStore
from app.redact.pii import PIIRedactor
from app.audit.logger import AuditLogger
from app.policies.engine import PolicyEngine

# Setup logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize components
sql_store = SQLStore()
vector_store = VectorStore()
redactor = PIIRedactor()
audit_logger = AuditLogger()
policy_engine = PolicyEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Synm Mediator...")
    await sql_store.init()
    await vector_store.init()
    await audit_logger.init()
    policy_engine.load_policies()
    yield
    logger.info("Shutting down Synm Mediator...")


app = FastAPI(
    title="Synm Mediator",
    description="Synm Personal AI Vault Mediator Service",
    version="0.1.0",
    lifespan=lifespan,
)


# Request/Response Models
class SessionRequest(BaseModel):
    """Session creation request."""
    profile: Optional[str] = "default"
    ttl_minutes: Optional[int] = Field(default=None, ge=1, le=1440)


class SessionResponse(BaseModel):
    """Session response."""
    session_id: str
    profile: str
    expires_at: str


class ContextRequest(BaseModel):
    """Context provisioning request."""
    session_id: str
    profile: str
    scopes: List[str]
    prompt: str
    max_tokens: Optional[int] = 1200


class ContextResponse(BaseModel):
    """Context response with redacted content."""
    context: str
    citations: List[Dict[str, str]]
    expires_at: str


class AuditExportRequest(BaseModel):
    """Audit export request."""
    format: str = "json"
    days: int = Field(default=7, ge=1, le=90)


# Dependency for PAT authentication
async def require_auth(authorization: str = Header(...)) -> str:
    """Verify PAT token from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    if not verify_pat(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return token


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "Synm Mediator", "version": "0.1.0", "status": "operational"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/v1/session", response_model=SessionResponse)
async def create_session(
    request: SessionRequest = SessionRequest(),
    token: str = Depends(require_auth)
) -> SessionResponse:
    """Create a new session for context provisioning."""
    session_id = str(uuid.uuid4())
    ttl_minutes = request.ttl_minutes or int(os.getenv("CONTEXT_TTL_MINUTES", "20"))
    expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
    
    # Store session
    await sql_store.create_session(
        session_id=session_id,
        profile=request.profile,
        expires_at=expires_at,
        user_token=token,
    )
    
    # Log audit event
    await audit_logger.log_event(
        event_type="session_created",
        session_id=session_id,
        profile=request.profile,
        metadata={"ttl_minutes": ttl_minutes},
    )
    
    return SessionResponse(
        session_id=session_id,
        profile=request.profile,
        expires_at=expires_at.isoformat() + "Z",
    )


@app.post("/v1/context", response_model=ContextResponse)
async def get_context(
    request: ContextRequest,
    token: str = Depends(require_auth)
) -> ContextResponse:
    """Get redacted context for a session."""
    # Validate session
    session = await sql_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if datetime.fromisoformat(session["expires_at"]) < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Session expired")
    
    # Check policy permissions
    if not policy_engine.check_access(request.profile, request.scopes):
        raise HTTPException(status_code=403, detail="Access denied for requested scopes")
    
    # Gather context from stores
    context_parts = []
    citations = []
    seen_content = set()  # Track content to avoid duplicates

    # Get data from vector store (semantic search)
    vector_results = await vector_store.search(
        query=request.prompt,
        scopes=request.scopes,
        limit=5,
    )

    for result in vector_results:
        content_hash = hash(result["content"].strip())
        if content_hash not in seen_content:
            context_parts.append(result["content"])
            seen_content.add(content_hash)
            citations.append({
                "type": "vector",
                "ref": result["source"],
                "score": str(result["score"]),
            })

    # Get data from SQL store (structured queries)
    for scope in request.scopes:
        scope_data = await sql_store.get_scope_data(scope)
        if scope_data:
            content_hash = hash(scope_data["content"].strip())
            if content_hash not in seen_content:
                context_parts.append(scope_data["content"])
                seen_content.add(content_hash)
                citations.append({
                    "type": "structured",
                    "ref": f"scope:{scope}",
                })

    # Combine and redact context
    raw_context = "\n\n".join(context_parts)
    redacted_context = await redactor.redact(
        text=raw_context,
        profile=request.profile,
        redaction_rules=policy_engine.get_redaction_rules(request.profile),
    )
    
    # Enforce size limits
    max_bytes = int(os.getenv("MAX_CONTEXT_BYTES", "20000"))
    if len(redacted_context.encode()) > max_bytes:
        redacted_context = redacted_context[:max_bytes].rsplit(' ', 1)[0] + "..."
    
    # Log audit event
    await audit_logger.log_event(
        event_type="context_provided",
        session_id=request.session_id,
        profile=request.profile,
        metadata={
            "scopes": request.scopes,
            "prompt_preview": request.prompt[:100],
            "context_size": len(redacted_context),
            "citations_count": len(citations),
        },
    )
    
    expires_at = datetime.utcnow() + timedelta(
        minutes=int(os.getenv("CONTEXT_TTL_MINUTES", "20"))
    )
    
    return ContextResponse(
        context=redacted_context,
        citations=citations,
        expires_at=expires_at.isoformat() + "Z",
    )


@app.post("/v1/revoke")
async def revoke_session(
    session_id: str,
    token: str = Depends(require_auth)
) -> Dict[str, str]:
    """Revoke a session immediately."""
    success = await sql_store.revoke_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await audit_logger.log_event(
        event_type="session_revoked",
        session_id=session_id,
        metadata={},
    )
    
    return {"message": "Session revoked successfully", "session_id": session_id}


@app.post("/v1/audit/export")
async def export_audit(
    request: AuditExportRequest,
    token: str = Depends(require_auth)
) -> Dict[str, Any]:
    """Export audit logs (admin only)."""
    # In production, add proper admin check here
    logs = await audit_logger.export_logs(
        format=request.format,
        days=request.days,
    )
    
    await audit_logger.log_event(
        event_type="audit_exported",
        session_id="admin",
        metadata={"format": request.format, "days": request.days},
    )
    
    return {"format": request.format, "logs": logs, "count": len(logs)}