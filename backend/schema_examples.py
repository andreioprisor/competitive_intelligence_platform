"""
Example usage of schema classes with the Company database model.
This shows how to serialize/deserialize profile and solutions data.
"""

from schemas import CompanyProfile, Solution
from db_models import Company


# Example 1: Deserialize from database
def load_company_profile(company: Company) -> CompanyProfile:
    """Load and deserialize company profile from database."""
    profile_obj = CompanyProfile.from_dict(company.profile)
    return profile_obj


def load_solutions(company: Company) -> list[Solution]:
    """Load and deserialize solutions from database."""
    solutions_objs = [Solution.from_dict(s) for s in company.solutions]
    return solutions_objs


# Example 2: Working with profile data
def get_company_info(company: Company):
    """Extract structured information from company profile."""
    profile = CompanyProfile.from_dict(company.profile)
    
    print(f"Company: {profile.name}")
    print(f"Industry: {profile.core_business.get('industry', 'Unknown')}")
    print(f"Competitors: {len(profile.competitors)}")
    
    for competitor in profile.competitors:
        print(f"  - {competitor.get('company_name')}: {competitor.get('website')}")


# Example 3: Working with solutions data
def analyze_solutions(company: Company):
    """Analyze solutions from company."""
    solutions = [Solution.from_dict(s) for s in company.solutions]
    
    for solution in solutions:
        print(f"\nSolution: {solution.title}")
        print(f"Features: {len(solution.features)}")
        print(f"Target Industries: {', '.join(solution.target_industries)}")
        
        # Access intelligence data
        positive_feedback = solution.customer_intelligence.get('positive_feedback', [])
        print(f"Positive reviews: {len(positive_feedback)}")


# Example 4: Validate and save to database
def save_validated_profile(db_session, domain: str, profile_data: dict, solutions_data: list):
    """Validate data using schemas before saving to database."""
    
    # Validate profile
    profile_obj = CompanyProfile.from_dict(profile_data)
    validated_profile = profile_obj.to_dict()
    
    # Validate solutions
    solutions_objs = [Solution.from_dict(s) for s in solutions_data]
    validated_solutions = [s.to_dict() for s in solutions_objs]
    
    # Save to database
    company = Company(
        domain=domain,
        profile=validated_profile,
        solutions=validated_solutions
    )
    
    db_session.add(company)
    db_session.commit()
    return company


# Example 5: Modify and update
def update_company_competitors(db_session, company: Company, new_competitors: list):
    """Update competitors list in company profile."""
    
    # Load current profile
    profile = CompanyProfile.from_dict(company.profile)
    
    # Update competitors
    profile.competitors.extend(new_competitors)
    
    # Save back to database
    company.profile = profile.to_dict()
    db_session.commit()
