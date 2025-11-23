"""
Simple schema classes for serialization/deserialization of company profiles and solutions.
These classes provide from_dict() and to_dict() methods for JSON JSONB field handling.
"""

from typing import List, Dict, Any


class CompanyProfile:
    """Company profile schema matching the prompt structure."""
    
    def __init__(self, name: str = "", core_business: Dict[str, Any] = None,
                 competitors: List[Dict[str, Any]] = None,
                 market_context: Dict[str, Any] = None,
                 enhanced_confidence: Dict[str, float] = None,
                 research_summary: Dict[str, Any] = None):
        self.name = name
        self.core_business = core_business or {}
        self.competitors = competitors or []
        self.market_context = market_context or {}
        self.enhanced_confidence = enhanced_confidence or {}
        self.research_summary = research_summary or {}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompanyProfile':
        """Create CompanyProfile from dictionary."""
        return cls(
            name=data.get("name", ""),
            core_business=data.get("core_business", {}),
            competitors=data.get("competitors", []),
            market_context=data.get("market_context", {}),
            enhanced_confidence=data.get("enhanced_confidence", {}),
            research_summary=data.get("research_summary", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert CompanyProfile to dictionary."""
        return {
            "name": self.name,
            "core_business": self.core_business,
            "competitors": self.competitors,
            "market_context": self.market_context,
            "enhanced_confidence": self.enhanced_confidence,
            "research_summary": self.research_summary
        }


class Solution:
    """Solution profile schema matching the prompt structure."""
    
    def __init__(self, title: str = "", description: str = "",
                 features: List[str] = None, benefits: List[str] = None,
                 use_cases: List[str] = None, target_industries: List[str] = None,
                 target_roles: List[str] = None, pricing_model: str = "",
                 pricing_value: str = "",
                 customer_intelligence: Dict[str, Any] = None,
                 competitive_intelligence: Dict[str, Any] = None,
                 market_intelligence: Dict[str, Any] = None,
                 pain_point_intelligence: Dict[str, Any] = None,
                 external_validation: Dict[str, Any] = None):
        self.title = title
        self.description = description
        self.features = features or []
        self.benefits = benefits or []
        self.use_cases = use_cases or []
        self.target_industries = target_industries or []
        self.target_roles = target_roles or []
        self.pricing_model = pricing_model
        self.pricing_value = pricing_value
        self.customer_intelligence = customer_intelligence or {}
        self.competitive_intelligence = competitive_intelligence or {}
        self.market_intelligence = market_intelligence or {}
        self.pain_point_intelligence = pain_point_intelligence or {}
        self.external_validation = external_validation or {}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Solution':
        """Create Solution from dictionary."""
        return cls(
            title=data.get("Title", data.get("title", "")),
            description=data.get("Description", data.get("description", "")),
            features=data.get("Features", data.get("features", [])),
            benefits=data.get("Benefits", data.get("benefits", [])),
            use_cases=data.get("Use_Cases", data.get("use_cases", [])),
            target_industries=data.get("Target_Industries", data.get("target_industries", [])),
            target_roles=data.get("Target_Roles", data.get("target_roles", [])),
            pricing_model=data.get("Pricing_Model", data.get("pricing_model", "")),
            pricing_value=data.get("Pricing_Value", data.get("pricing_value", "")),
            customer_intelligence=data.get("customer_intelligence", {}),
            competitive_intelligence=data.get("competitive_intelligence", {}),
            market_intelligence=data.get("market_intelligence", {}),
            pain_point_intelligence=data.get("pain_point_intelligence", {}),
            external_validation=data.get("external_validation", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Solution to dictionary."""
        return {
            "Title": self.title,
            "Description": self.description,
            "Features": self.features,
            "Benefits": self.benefits,
            "Use_Cases": self.use_cases,
            "Target_Industries": self.target_industries,
            "Target_Roles": self.target_roles,
            "Pricing_Model": self.pricing_model,
            "Pricing_Value": self.pricing_value,
            "customer_intelligence": self.customer_intelligence,
            "competitive_intelligence": self.competitive_intelligence,
            "market_intelligence": self.market_intelligence,
            "pain_point_intelligence": self.pain_point_intelligence,
            "external_validation": self.external_validation
        }
