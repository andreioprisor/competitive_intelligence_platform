#!/usr/bin/env python3
"""
FastAPI backend for company profile and solutions analysis.

Endpoints:
  GET /profile_competitors_solution - Generate company profile and solutions list
  GET /health - Health check
"""

import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api_clients.gemini_adapter import GeminiAPI

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
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        return json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse {field_name} JSON: {e}")
        logger.error(f"Response was: {response[:500]}...")
        raise ValueError(f"Invalid JSON response for {field_name}")


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
            model_name="gemini-2.5-pro",
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
            model_name="gemini-2.5-pro",
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
    description="Analyzes a company domain and returns its profile, competitors, and solutions with comprehensive market intelligence"
)
async def profile_competitors_solution(
    domain: str = Query(
        ...,
        description="Company domain (e.g., 'stripe.com' or 'https://stripe.com')",
        example="stripe.com"
    ),
    model: str = Query(
        "gemini-2.5-pro",
        description="Gemini model to use",
        example="gemini-2.5-pro"
    )
) -> ProfileCompetitorsSolutionResponse:
    """
    Generate company profile and solutions analysis for a given domain.
    
    This endpoint:
    1. Searches for company information using the company domain
    2. Generates a comprehensive company profile with competitors and market context
    3. Analyzes the company's solutions/products with competitive intelligence
    4. Returns both profiles in a single response
    
    Args:
        domain: Company domain (e.g., 'stripe.com')
        model: Gemini model to use (default: 'gemini-2.5-pro')
    
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
        
        # Initialize Gemini API
        gemini_api = GeminiAPI(model_id=model)
        logger.info(f"Initialized Gemini API with model: {model}")
        
        # Step 1: Generate company profile
        logger.info("Starting company profile generation...")
        company_profile = generate_company_profile(gemini_api, clean_domain_str)
        
        # Step 2: Generate solutions profile
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
            "industry": company_profile.get("core_business", {}).get("industry", "Unknown")
        }
        
        logger.info(f"Analysis complete for {clean_domain_str}")
        
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


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Company Intelligence API server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
