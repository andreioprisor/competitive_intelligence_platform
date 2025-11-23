from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Company(Base):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    domain = Column(String, unique=True, nullable=False, index=True)
    solutions = Column(JSONB, default={})
    profile = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    
    # Relationships
    competitors = relationship("Competitor", back_populates="company", cascade="all, delete-orphan")
    criterias = relationship("Criteria", back_populates="company", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Company(id={self.id}, domain='{self.domain}')>"


class Competitor(Base):
    __tablename__ = 'competitors'
    
    id = Column(Integer, primary_key=True)
    domain = Column(String, nullable=False, index=True)
    solutions = Column(JSONB, default={})
    company_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="competitors")
    values = relationship("Value", back_populates="competitor", cascade="all, delete-orphan")
    
    # Index for faster lookups
    __table_args__ = (
        Index('ix_competitors_company_domain', 'company_id', 'domain'),
        UniqueConstraint('company_id', 'domain', name='uq_competitor_company_domain'),
    )
    
    def __repr__(self):
        return f"<Competitor(id={self.id}, domain='{self.domain}', company_id={self.company_id})>"


class Criteria(Base):
    __tablename__ = 'criterias'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    definition = Column(String)
    company_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="criterias")
    values = relationship("Value", back_populates="criteria", cascade="all, delete-orphan")
    
    # Index for faster lookups
    __table_args__ = (
        Index('ix_criterias_company_name', 'company_id', 'name'),
    )
    
    def __repr__(self):
        return f"<Criteria(id={self.id}, name='{self.name}', company_id={self.company_id})>"


class Value(Base):
    __tablename__ = 'values'
    
    id = Column(Integer, primary_key=True)
    criteria_id = Column(Integer, ForeignKey('criterias.id', ondelete='CASCADE'), nullable=False)
    competitor_id = Column(Integer, ForeignKey('competitors.id', ondelete='CASCADE'), nullable=False)
    value = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    criteria = relationship("Criteria", back_populates="values")
    competitor = relationship("Competitor", back_populates="values")
    
    # Indexes for faster lookups
    __table_args__ = (
        Index('ix_values_criteria_competitor', 'criteria_id', 'competitor_id', unique=True),
    )
    
    def __repr__(self):
        return f"<Value(id={self.id}, criteria_id={self.criteria_id}, competitor_id={self.competitor_id})>"