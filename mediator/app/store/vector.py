"""Vector store adapter using ChromaDB."""

import os
import logging
from typing import List, Dict, Any, Optional
import httpx
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector storage adapter for semantic search."""
    
    def __init__(self):
        self.chroma_url = os.getenv("CHROMA_URL", "http://chroma:8000")
        self.collection_name = "synm_vault"
        self.client = None
        self.collection = None
    
    async def init(self) -> None:
        """Initialize connection to ChromaDB."""
        try:
            # Connect to ChromaDB server
            # Use simple client without tenant/database for simpler setup
            self.client = chromadb.HttpClient(
                host=self.chroma_url,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(self.collection_name)
                logger.info(f"Using existing collection: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info(f"Created new collection: {self.collection_name}")
                
        except Exception as e:
            logger.warning(f"ChromaDB connection failed: {e}. Running in degraded mode.")
            self.client = None
            self.collection = None
    
    async def search(
        self,
        query: str,
        scopes: List[str],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents based on query and scopes."""
        if not self.collection:
            logger.warning("Vector store not available, returning empty results")
            return []
        
        try:
            # Build metadata filter for scopes
            where_clause = None
            if scopes:
                where_clause = {"scope": {"$in": scopes}}
            
            # Perform similarity search
            results = self.collection.query(
                query_texts=[query],
                n_results=min(limit, 10),
                where=where_clause if where_clause else None,
            )
            
            # Format results
            formatted_results = []
            if results and results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        "content": doc,
                        "source": results['metadatas'][0][i].get('source', 'unknown') if results['metadatas'] else 'unknown',
                        "score": results['distances'][0][i] if results['distances'] else 0.0,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def index_document(
        self,
        content: str,
        source: str,
        scope: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Index a document in the vector store."""
        if not self.collection:
            logger.warning("Vector store not available, cannot index document")
            return False
        
        try:
            # Prepare metadata
            doc_metadata = {
                "source": source,
                "scope": scope,
                **(metadata or {}),
            }
            
            # Generate a unique ID based on source
            doc_id = f"{scope}:{source}".replace("/", "_").replace(" ", "_")
            
            # Add to collection
            self.collection.add(
                documents=[content],
                metadatas=[doc_metadata],
                ids=[doc_id],
            )
            
            logger.info(f"Indexed document: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return False
    
    async def delete_by_scope(self, scope: str) -> bool:
        """Delete all documents for a specific scope."""
        if not self.collection:
            return False
        
        try:
            self.collection.delete(
                where={"scope": scope}
            )
            logger.info(f"Deleted documents for scope: {scope}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        if not self.collection:
            return {"status": "unavailable"}
        
        try:
            count = self.collection.count()
            return {
                "status": "available",
                "collection": self.collection_name,
                "document_count": count,
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"status": "error", "error": str(e)}