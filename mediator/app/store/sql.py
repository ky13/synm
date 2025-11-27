"""SQL store adapter using SQLModel/SQLAlchemy."""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class SessionModel(SQLModel, table=True):
    """Session model for tracking context sessions."""
    __tablename__ = "sessions"
    
    id: str = Field(primary_key=True)
    profile: str
    expires_at: datetime
    user_token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    revoked: bool = Field(default=False)


class ScopeData(SQLModel, table=True):
    """Structured data for scopes."""
    __tablename__ = "scope_data"

    id: int = Field(primary_key=True)
    scope: str = Field(index=True)
    content: str
    meta_data: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SQLStore:
    """SQL storage adapter for structured data."""
    
    def __init__(self):
        db_path = os.getenv("SQLITE_PATH", "/app/data/mediator.sqlite")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Use async SQLite
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init(self) -> None:
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("SQL store initialized")
    
    async def create_session(
        self,
        session_id: str,
        profile: str,
        expires_at: datetime,
        user_token: str,
    ) -> SessionModel:
        """Create a new session."""
        async with self.async_session() as session:
            db_session = SessionModel(
                id=session_id,
                profile=profile,
                expires_at=expires_at,
                user_token=user_token,
            )
            session.add(db_session)
            await session.commit()
            return db_session
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        async with self.async_session() as session:
            statement = select(SessionModel).where(
                SessionModel.id == session_id,
                SessionModel.revoked == False,
            )
            result = await session.execute(statement)
            db_session = result.scalar_one_or_none()
            
            if db_session:
                return {
                    "id": db_session.id,
                    "profile": db_session.profile,
                    "expires_at": db_session.expires_at.isoformat(),
                    "created_at": db_session.created_at.isoformat(),
                }
            return None
    
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a session."""
        async with self.async_session() as session:
            statement = select(SessionModel).where(SessionModel.id == session_id)
            result = await session.execute(statement)
            db_session = result.scalar_one_or_none()
            
            if db_session:
                db_session.revoked = True
                session.add(db_session)
                await session.commit()
                return True
            return False
    
    async def get_scope_data(self, scope: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific scope."""
        async with self.async_session() as session:
            statement = select(ScopeData).where(
                ScopeData.scope == scope
            ).order_by(ScopeData.updated_at.desc())
            result = await session.execute(statement)
            scope_data = result.first()
            
            if scope_data and scope_data[0]:
                return {
                    "content": scope_data[0].content,
                    "metadata": scope_data[0].meta_data,
                    "updated_at": scope_data[0].updated_at.isoformat(),
                }
            return None
    
    async def store_scope_data(
        self,
        scope: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store or update scope data."""
        import json
        
        async with self.async_session() as session:
            # Check if scope exists
            statement = select(ScopeData).where(ScopeData.scope == scope)
            result = await session.execute(statement)
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.content = content
                existing.meta_data = json.dumps(metadata or {})
                existing.updated_at = datetime.utcnow()
                session.add(existing)
            else:
                new_scope = ScopeData(
                    scope=scope,
                    content=content,
                    meta_data=json.dumps(metadata or {}),
                )
                session.add(new_scope)
            
            await session.commit()