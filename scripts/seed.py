"""Seed script to index sample notes and create demo policies."""

import asyncio
import os
import sys
from pathlib import Path
import logging

# Add the mediator app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mediator'))

from app.store.sql import SQLStore
from app.store.vector import VectorStore

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_data():
    """Seed the vault with sample data."""
    logger.info("Starting data seeding...")
    
    # Initialize stores
    sql_store = SQLStore()
    vector_store = VectorStore()
    
    await sql_store.init()
    await vector_store.init()
    
    # Read sample notes
    notes_dir = Path(__file__).parent.parent / "notes"
    
    # Index bio.md
    bio_file = notes_dir / "bio.md"
    if bio_file.exists():
        content = bio_file.read_text()
        
        # Store in SQL for structured access
        await sql_store.store_scope_data(
            scope="bio.basic",
            content=content,
            metadata={"source": "notes/bio.md", "type": "bio"},
        )
        
        # Index in vector store for semantic search
        await vector_store.index_document(
            content=content,
            source="notes/bio.md",
            scope="bio.basic",
            metadata={"type": "bio", "last_updated": "2024-01-01"},
        )
        
        logger.info("Indexed bio.md")
    
    # Index projects.md
    projects_file = notes_dir / "projects.md"
    if projects_file.exists():
        content = projects_file.read_text()
        
        await sql_store.store_scope_data(
            scope="projects.recent",
            content=content,
            metadata={"source": "notes/projects.md", "type": "projects"},
        )
        
        await vector_store.index_document(
            content=content,
            source="notes/projects.md",
            scope="projects.recent",
            metadata={"type": "projects", "last_updated": "2024-01-01"},
        )
        
        logger.info("Indexed projects.md")
    
    # Add some additional sample data
    sample_resume = """
    PROFESSIONAL SUMMARY
    Cloud Engineer with 5+ years of experience in AWS, GCP, and automation.
    Specializes in infrastructure as code, CI/CD pipelines, and security hardening.
    
    TECHNICAL SKILLS
    - Cloud Platforms: AWS, GCP, Azure
    - IaC: Terraform, CloudFormation, Pulumi
    - CI/CD: Jenkins, GitLab CI, GitHub Actions
    - Security: IAM, VPC, security modeling
    - Languages: Python, Go, Bash
    """
    
    await sql_store.store_scope_data(
        scope="resume.public",
        content=sample_resume,
        metadata={"source": "generated", "type": "resume"},
    )
    
    await vector_store.index_document(
        content=sample_resume,
        source="resume_public",
        scope="resume.public",
        metadata={"type": "resume", "visibility": "public"},
    )
    
    logger.info("Indexed sample resume data")
    
    # Get collection stats
    stats = await vector_store.get_collection_stats()
    logger.info(f"Vector store stats: {stats}")
    
    logger.info("Data seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())