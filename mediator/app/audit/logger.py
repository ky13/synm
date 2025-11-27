"""Append-only audit logger."""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib
import sqlite3
import aiosqlite

logger = logging.getLogger(__name__)


class AuditLogger:
    """Append-only audit logger with tamper detection."""
    
    def __init__(self):
        audit_path = os.getenv("SQLITE_PATH", "/app/data/mediator.sqlite")
        self.audit_db = audit_path.replace("mediator.sqlite", "audit.sqlite")
        Path(self.audit_db).parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
    
    async def init(self) -> None:
        """Initialize audit database."""
        async with aiosqlite.connect(self.audit_db) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    session_id TEXT,
                    profile TEXT,
                    user_token_hash TEXT,
                    metadata TEXT,
                    hash TEXT NOT NULL,
                    previous_hash TEXT
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id ON audit_log(session_id)
            """)
            await db.commit()
        
        logger.info("Audit logger initialized")
    
    async def log_event(
        self,
        event_type: str,
        session_id: Optional[str] = None,
        profile: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_token: Optional[str] = None,
    ) -> None:
        """Log an audit event."""
        timestamp = datetime.utcnow().isoformat()
        
        # Hash user token if provided
        user_token_hash = None
        if user_token:
            user_token_hash = hashlib.sha256(user_token.encode()).hexdigest()[:16]
        
        # Get previous hash for chain integrity
        previous_hash = await self._get_last_hash()
        
        # Create event record
        event_data = {
            "timestamp": timestamp,
            "event_type": event_type,
            "session_id": session_id,
            "profile": profile,
            "user_token_hash": user_token_hash,
            "metadata": metadata or {},
        }
        
        # Calculate hash for this event
        event_hash = self._calculate_hash(event_data, previous_hash)
        
        # Store in database
        async with aiosqlite.connect(self.audit_db) as db:
            await db.execute("""
                INSERT INTO audit_log 
                (timestamp, event_type, session_id, profile, user_token_hash, metadata, hash, previous_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                event_type,
                session_id,
                profile,
                user_token_hash,
                json.dumps(metadata or {}),
                event_hash,
                previous_hash,
            ))
            await db.commit()
        
        logger.debug(f"Audit event logged: {event_type} for session {session_id}")
    
    async def export_logs(
        self,
        format: str = "json",
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Export audit logs for specified period."""
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(self.audit_db) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM audit_log 
                WHERE timestamp >= ? 
                ORDER BY timestamp DESC
            """, (cutoff_date,)) as cursor:
                rows = await cursor.fetchall()
        
        logs = []
        for row in rows:
            log_entry = {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "event_type": row["event_type"],
                "session_id": row["session_id"],
                "profile": row["profile"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "hash": row["hash"],
            }
            logs.append(log_entry)
        
        if format == "csv":
            # Convert to CSV format (simplified)
            return self._to_csv(logs)
        
        return logs
    
    async def verify_integrity(self) -> bool:
        """Verify the integrity of the audit log chain."""
        async with aiosqlite.connect(self.audit_db) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM audit_log ORDER BY id
            """) as cursor:
                rows = await cursor.fetchall()
        
        if not rows:
            return True
        
        # Verify chain integrity
        for i, row in enumerate(rows):
            if i == 0:
                if row["previous_hash"] is not None:
                    logger.error("First audit entry has non-null previous hash")
                    return False
            else:
                # Recalculate hash and verify
                event_data = {
                    "timestamp": row["timestamp"],
                    "event_type": row["event_type"],
                    "session_id": row["session_id"],
                    "profile": row["profile"],
                    "user_token_hash": row["user_token_hash"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
                
                calculated_hash = self._calculate_hash(event_data, row["previous_hash"])
                if calculated_hash != row["hash"]:
                    logger.error(f"Hash mismatch at audit entry {row['id']}")
                    return False
                
                # Verify chain link
                if row["previous_hash"] != rows[i-1]["hash"]:
                    logger.error(f"Chain broken at audit entry {row['id']}")
                    return False
        
        logger.info("Audit log integrity verified")
        return True
    
    async def _get_last_hash(self) -> Optional[str]:
        """Get the hash of the last audit entry."""
        async with aiosqlite.connect(self.audit_db) as db:
            async with db.execute("""
                SELECT hash FROM audit_log 
                ORDER BY id DESC LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    
    def _calculate_hash(self, event_data: Dict[str, Any], previous_hash: Optional[str]) -> str:
        """Calculate hash for an audit event."""
        # Create canonical representation
        canonical = json.dumps(event_data, sort_keys=True)
        
        # Include previous hash in calculation
        if previous_hash:
            canonical = f"{previous_hash}:{canonical}"
        
        # Calculate SHA-256 hash
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def _to_csv(self, logs: List[Dict[str, Any]]) -> List[str]:
        """Convert logs to CSV format."""
        if not logs:
            return []
        
        # Header
        csv_lines = ["timestamp,event_type,session_id,profile,metadata"]
        
        # Data rows
        for log in logs:
            metadata_str = json.dumps(log.get("metadata", {}))
            csv_lines.append(
                f"{log['timestamp']},{log['event_type']},{log.get('session_id', '')},"
                f"{log.get('profile', '')},{metadata_str}"
            )
        
        return csv_lines