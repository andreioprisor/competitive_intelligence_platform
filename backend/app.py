#!/usr/bin/env python3
"""
FastAPI backend for company profile and solutions analysis.

Endpoints:
  GET /profile_competitors_solution - Generate company profile and solutions list
  POST /save_company_profile - Save company profile to database and run agentic pipeline
  GET /health - Health check
"""

import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api_clients.gemini_adapter import GeminiAPI
from database import get_db
from db_models import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the workspace root directory
WORKSPACE_ROOT = Path(__file__).parent
PROMPTS_DIR = WORKSPACE_ROOT / "prompts"

# Initialize FastAPI app
app = FastAPI(
    title="Company Intelligence API",
    description="API for generating company profiles and solutions analysis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response models
class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Health status")
    message: str = Field(..., description="Status message")


class ProfileCompetitorsSolutionResponse(BaseModel):
    """Response model for profile competitors solution endpoint."""
    domain: str = Field(..., description="Company domain analyzed")
    company_profile: Dict[str, Any] = Field(..., description="Company profile JSON")
    solutions_profile: List[Dict[str, Any]] = Field(..., description="Solutions profile array")
    analysis_metadata: Dict[str, Any] = Field(..., description="Analysis metadata")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error detail")


class SaveCompanyProfileRequest(BaseModel):
    """Request model for saving company profile."""
    domain: str = Field(..., description="Company domain")
    company_profile: Dict[str, Any] = Field(..., description="Company profile JSON")
    solutions_profile: List[Dict[str, Any]] = Field(..., description="Solutions profile array")
    analysis_metadata: Dict[str, Any] = Field(..., description="Analysis metadata")


class SaveCompanyProfileResponse(BaseModel):
    """Response model for save company profile endpoint."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")
    profile_id: int = Field(..., description="Database ID of the saved profile")
    domain: str = Field(..., description="Company domain")
    agentic_pipeline_result: Dict[str, Any] = Field(..., description="Result from agentic pipeline (mock for now)")


def load_prompt_template(prompt_name: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = PROMPTS_DIR / prompt_name
    if not prompt_path.exists():
        logger.error(f"Prompt file not found: {prompt_path}")
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def clean_domain(domain: str) -> str:
    """Clean up domain input."""
    domain = domain.lower().strip()
    if domain.startswith("http://"):
        domain = domain[7:]
    if domain.startswith("https://"):
        domain = domain[8:]
    if domain.endswith("/"):
        domain = domain[:-1]
    return domain


def parse_json_response(response: str, field_name: str) -> Any:
    """Parse JSON from response text, handling markdown code blocks."""
    try:
        cleaned_response = response.strip()
        
        # Handle case where response has text before the JSON code block
        if "```json" in cleaned_response:
            # Extract content between ```json and ```
            start_marker = "```json"
            end_marker = "```"
            
            start_idx = cleaned_response.find(start_marker)
            if start_idx != -1:
                # Start after the ```json marker
                start_idx += len(start_marker)
                # Find the closing ``` after the start
                end_idx = cleaned_response.find(end_marker, start_idx)
                if end_idx != -1:
                    cleaned_response = cleaned_response[start_idx:end_idx]
                else:
                    # No closing marker, take everything after ```json
                    cleaned_response = cleaned_response[start_idx:]
        
        cleaned_response = cleaned_response.strip()
        
        return json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse {field_name} JSON: {e}")
        logger.error(f"Response was: {response[:500]}...")
        raise ValueError(f"Invalid JSON response for {field_name}")


def run_agentic_pipeline(profile_data: dict) -> dict:
    """
    Run the agentic pipeline on the company profile data.
    
    TODO: Implement actual agentic pipeline.
    
    Args:
        profile_data: Dict containing company_profile, solutions_profile, analysis_metadata
    
    Returns:
        dict: Result from the agentic pipeline
    """
    logger.info("Running agentic pipeline (mock)")
    
    # Mock agentic pipeline result
    # This will be replaced with the actual pipeline implementation
    mock_result = {
        "status": "pipeline_completed",
        "processing_stage": "mock_implementation",
        "company_name": profile_data.get("company_profile", {}).get("name", "Unknown"),
        "domain": profile_data.get("domain", "Unknown"),
        "pipeline_results": {
            "market_analysis": {
                "market_size": "MOCK DATA - Replace with actual analysis",
                "growth_rate": "MOCK DATA",
                "key_trends": []
            },
            "competitive_positioning": {
                "strengths": [],
                "weaknesses": [],
                "opportunities": [],
                "threats": []
            },
            "strategic_recommendations": {
                "short_term": [],
                "long_term": []
            }
        },
        "confidence_score": 0.0,
        "note": "This is a mock response. Implement the actual agentic pipeline in the run_agentic_pipeline function."
    }
    
    return mock_result


def generate_company_profile(gemini_api: GeminiAPI, domain: str) -> dict:
    """
    Generate a company profile for the given domain.
    
    Args:
        gemini_api: GeminiAPI instance
        domain: Company domain (e.g., "example.com")
    
    Returns:
        dict: Parsed company profile JSON
    """
    logger.info(f"Generating company profile for domain: {domain}")
    
    # Load the company profile prompt template
    template = load_prompt_template("company_profile.md")
    
    # Create the search query
    search_query = f"""
Please analyze the company at domain {domain} and generate a comprehensive company profile.

Use Web Search Grounding to:
1. Find website content about the company
2. Find LinkedIn company information
3. Research competitors in the market
4. Validate market position and offerings

Then generate the JSON profile according to the OUTPUT_STRUCTURE.

Company Domain: {domain}

{template}
"""
    
    try:
        # Get the response from Gemini with Google Search
        response = gemini_api.get_google_search_response(
            prompt=search_query,
            model_name="gemini-3-pro-preview",
            thinking_budget=2000,
            temperature=0.7
        )
        
        # Parse the JSON response
        logger.info("Parsing company profile response")
        profile = parse_json_response(response, "company profile")
        logger.info(f"Successfully generated profile for {domain}")
        return profile
        
    except Exception as e:
        logger.error(f"Error generating company profile: {e}")
        raise


def generate_solutions_profile(gemini_api: GeminiAPI, domain: str, company_profile: dict) -> list:
    """
    Generate solutions profile based on company profile.
    
    Args:
        gemini_api: GeminiAPI instance
        domain: Company domain
        company_profile: Company profile dict from generate_company_profile
    
    Returns:
        list: Parsed solutions profile JSON array
    """
    logger.info(f"Generating solutions profile for {domain}")
    
    # Load the solutions profile prompt template
    template = load_prompt_template("solutions_profile.md")
    
    # Convert company profile to formatted string
    company_profile_str = json.dumps(company_profile, indent=2)
    
    # Create the search query
    search_query = f"""
Please analyze the solutions provided by {domain} based on the following company profile and their website content.

Use Web Search Grounding to:
1. Find information about each solution/product
2. Gather customer reviews and testimonials
3. Identify competitive alternatives
4. Research market adoption and pricing
5. Validate benefits and use cases

Company Profile:
{company_profile_str}

{template}

Generate the JSON array of enhanced solution profiles according to the FINAL OUTPUT STRUCTURE.
"""
    
    try:
        # Get the response from Gemini with Google Search
        response = gemini_api.get_google_search_response(
            prompt=search_query,
            model_name="gemini-3-pro-preview",
            thinking_budget=3000,
            temperature=0.7
        )
        
        # Parse the JSON response
        logger.info("Parsing solutions profile response")
        solutions = parse_json_response(response, "solutions profile")
        
        if not isinstance(solutions, list):
            logger.warning("Solutions profile is not a list, wrapping it")
            solutions = [solutions] if solutions else []
        
        logger.info(f"Successfully generated {len(solutions)} solution profiles")
        return solutions
        
    except Exception as e:
        logger.error(f"Error generating solutions profile: {e}")
        raise


@app.post(
    "/save_company_profile",
    response_model=SaveCompanyProfileResponse,
    summary="Save Company Profile and Run Agentic Pipeline",
    description="Saves a company profile to the database and runs the agentic pipeline for deeper analysis"
)
async def save_company_profile(
    request: SaveCompanyProfileRequest,
    db: Session = Depends(get_db)
) -> SaveCompanyProfileResponse:
    """
    Save company profile to database and run agentic pipeline.
    
    This endpoint:
    1. Receives a company profile (same format as GET /profile_competitors_solution returns)
    2. Saves the profile data to the database using SQLAlchemy
    3. Runs the agentic pipeline (currently mock) on the profile data
    4. Returns the agentic pipeline result
    
    Args:
        request: SaveCompanyProfileRequest containing domain, company_profile, solutions_profile, analysis_metadata
        db: Database session (injected)
    
    Returns:
        SaveCompanyProfileResponse: Success status and agentic pipeline results
    
    Raises:
        HTTPException: If saving to database fails or domain already exists
    """
    try:
        logger.info(f"Received save request for domain: {request.domain}")
        
        # Optional: Validate and serialize using schema classes
        # profile_obj = CompanyProfileSchema.from_dict(request.company_profile)
        # solutions_objs = [SolutionSchema.from_dict(s) for s in request.solutions_profile]
        # validated_profile = profile_obj.to_dict()
        # validated_solutions = [s.to_dict() for s in solutions_objs]
        
        # Check if company already exists
        existing_company = db.query(Company).filter(
            Company.domain == request.domain
        ).first()
        
        if existing_company:
            # Update existing company
            logger.info(f"Company already exists for domain: {request.domain}, updating...")
            existing_company.profile = request.company_profile
            existing_company.solutions = request.solutions_profile
            db.commit()
            db.refresh(existing_company)
            logger.info(f"✓ Successfully updated company with ID: {existing_company.id}")
            company = existing_company
            operation = "updated"
        else:
            # Create new company instance
            logger.info(f"Creating new database record for {request.domain}")
            company = Company(
                domain=request.domain,
                profile=request.company_profile,
                solutions=request.solutions_profile
            )
            
            # Save to database
            db.add(company)
            db.commit()
            db.refresh(company)
            
            logger.info(f"✓ Successfully saved company to database with ID: {company.id}")
            operation = "created"
        
        # Run agentic pipeline
        logger.info(f"Starting agentic pipeline for {request.domain}")
        pipeline_result = run_agentic_pipeline(request.dict())
        
        logger.info(f"Agentic pipeline completed for {request.domain}")
        
        action_message = "updated" if operation == "updated" else "saved"
        return SaveCompanyProfileResponse(
            success=True,
            message=f"Profile {action_message} successfully for {request.domain}",
            profile_id=company.id,
            domain=request.domain,
            agentic_pipeline_result=pipeline_result
        )
        
    except HTTPException:
        raise
    except IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Profile already exists for this domain"
        )
    except Exception as e:
        logger.error(f"Error saving profile: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error saving profile: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthResponse: API health status
    """
    return HealthResponse(
        status="healthy",
        message="API is running"
    )


@app.get(
    "/profile_competitors_solution",
    response_model=ProfileCompetitorsSolutionResponse,
    summary="Generate Company Profile and Solutions Analysis",
    description="Analyzes a company domain and returns its profile, competitors, and solutions with comprehensive market intelligence. Returns cached data from database if available."
)
async def profile_competitors_solution(
    domain: str = Query(
        ...,
        description="Company domain (e.g., 'stripe.com' or 'https://stripe.com')",
        example="stripe.com"
    ),
    model: str = Query(
        "gemini-3-pro-preview",
        description="Gemini model to use",
        example="gemini-3-pro-preview"
    ),
    db: Session = Depends(get_db)
) -> ProfileCompetitorsSolutionResponse:
    """
    Generate company profile and solutions analysis for a given domain.
    
    This endpoint:
    1. First checks if the profile exists in the database and returns it instantly
    2. If not found, searches for company information using the company domain
    3. Generates a comprehensive company profile with competitors and market context
    4. Analyzes the company's solutions/products with competitive intelligence
    5. Returns both profiles in a single response
    
    Args:
        domain: Company domain (e.g., 'stripe.com')
        model: Gemini model to use (default: 'gemini-2.5-pro')
        db: Database session (injected)
    
    Returns:
        ProfileCompetitorsSolutionResponse: Company profile and solutions profiles
    
    Raises:
        HTTPException: If analysis fails
    """
    try:
        # Clean up domain input
        clean_domain_str = clean_domain(domain)
        logger.info(f"Processing request for domain: {clean_domain_str}")
        
        # Validate domain format
        if not clean_domain_str or '.' not in clean_domain_str:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid domain format: {domain}"
            )
        
        # Step 1: Check if company exists in database
        logger.info(f"Checking database for cached profile: {clean_domain_str}")
        cached_company = db.query(Company).filter(
            Company.domain == clean_domain_str
        ).first()
        
        if cached_company:
            logger.info(f"✓ Found cached company in database for {clean_domain_str}")
            
            # Optional: Deserialize using schema classes for validation/manipulation
            # profile_obj = CompanyProfileSchema.from_dict(cached_company.profile)
            # solutions_objs = [SolutionSchema.from_dict(s) for s in cached_company.solutions]
            
            return ProfileCompetitorsSolutionResponse(
                domain=cached_company.domain,
                company_profile=cached_company.profile,
                solutions_profile=cached_company.solutions,
                analysis_metadata={
                    "source": "database_cache",
                    "cached": True,
                    "company_id": cached_company.id
                }
            )
        
        logger.info(f"Profile not found in database, generating new analysis for {clean_domain_str}")
        
        # Initialize Gemini API
        gemini_api = GeminiAPI(model_id=model)
        logger.info(f"Initialized Gemini API with model: {model}")
        
        # Step 2: Generate company profile
        logger.info("Starting company profile generation...")
        company_profile = generate_company_profile(gemini_api, clean_domain_str)
        
        # Step 3: Generate solutions profile
        logger.info("Starting solutions profile generation...")
        solutions_profile = generate_solutions_profile(gemini_api, clean_domain_str, company_profile)
        
        # Prepare metadata
        analysis_metadata = {
            "input_tokens": gemini_api.input_tokens,
            "output_tokens": gemini_api.output_tokens,
            "thinking_tokens": gemini_api.thinking_tokens,
            "model_used": model,
            "company_name": company_profile.get("name", "Unknown"),
            "solutions_count": len(solutions_profile),
            "industry": company_profile.get("core_business", {}).get("industry", "Unknown"),
            "source": "generated",
            "cached": False
        }
        
        logger.info(f"Analysis complete for {clean_domain_str}")
        
        # Step 4: Auto-save the generated profile to the database
        logger.info(f"Auto-saving generated profile to database for {clean_domain_str}")
        try:
            # Optional: Validate using schema classes before saving
            # profile_obj = CompanyProfileSchema.from_dict(company_profile)
            # validated_profile = profile_obj.to_dict()
            # solutions_objs = [SolutionSchema.from_dict(s) for s in solutions_profile]
            # validated_solutions = [s.to_dict() for s in solutions_objs]
            
            new_company = Company(
                domain=clean_domain_str,
                profile=company_profile,  # Store raw dict in JSONB
                solutions=solutions_profile  # Store raw list in JSONB
            )
            db.add(new_company)
            db.commit()
            logger.info(f"✓ Profile auto-saved to database with ID: {new_company.id}")
        except IntegrityError:
            db.rollback()
            logger.warning(f"Company already exists in database, skipping auto-save")
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to auto-save company: {e}")
        
        return ProfileCompetitorsSolutionResponse(
            domain=clean_domain_str,
            company_profile=company_profile,
            solutions_profile=solutions_profile,
            analysis_metadata=analysis_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing domain: {str(e)}"
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request failed",
            "detail": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred"
        }
    )


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Initializing database on startup...")
    logger.info("Database initialization complete")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Company Intelligence API server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
