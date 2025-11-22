"""
Database models for company profiles.
"""

import logging
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import mapped_column
from db_config import Base

logger = logging.getLogger(__name__)


class CompanyProfile(Base):
    """
    SQLAlchemy model for storing company profiles with their analysis data.
    """
    __tablename__ = "company_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Company identifiers
    domain = Column(String(255), unique=True, index=True, nullable=False)
    company_name = Column(String(255), nullable=True)
    
    # Full profile data stored as JSON
    company_profile = Column(JSON, nullable=False)
    solutions_profile = Column(JSON, nullable=False)
    analysis_metadata = Column(JSON, nullable=False)
    
    # Agentic pipeline result (populated after pipeline runs)
    agentic_pipeline_result = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<CompanyProfile(domain={self.domain}, company_name={self.company_name}, created_at={self.created_at})>"
    
    @classmethod
    def from_profile_response(cls, domain: str, response_data: dict):
        """
        Create a CompanyProfile instance from a ProfileCompetitorsSolutionResponse.
        
        Args:
            domain: Company domain
            response_data: Dict with keys: company_profile, solutions_profile, analysis_metadata
        
        Returns:
            CompanyProfile instance
        """
        company_name = response_data.get("company_profile", {}).get("name", None)
        
        return cls(
            domain=domain,
            company_name=company_name,
            company_profile=response_data.get("company_profile", {}),
            solutions_profile=response_data.get("solutions_profile", []),
            analysis_metadata=response_data.get("analysis_metadata", {})
        )
    
    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "domain": self.domain,
            "company_name": self.company_name,
            "company_profile": self.company_profile,
            "solutions_profile": self.solutions_profile,
            "analysis_metadata": self.analysis_metadata,
            "agentic_pipeline_result": self.agentic_pipeline_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
