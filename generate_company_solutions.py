#!/usr/bin/env python3
"""
Script to generate company profile and solutions analysis using Gemini API.

This script:
1. Takes a company domain as input
2. Generates a company profile using the company_profile.md prompt
3. Generates a solutions list using the solutions_profile.md prompt
4. Outputs both results to JSON files
"""

import json
import sys
import argparse
from pathlib import Path
from api_clients.gemini_adapter import GeminiAPI
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the workspace root directory
WORKSPACE_ROOT = Path(__file__).parent
PROMPTS_DIR = WORKSPACE_ROOT / "prompts"


def load_prompt_template(prompt_name: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = PROMPTS_DIR / prompt_name
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def generate_company_profile(gemini_api: GeminiAPI, company_domain: str) -> dict:
    """
    Generate a company profile for the given domain.
    
    Args:
        gemini_api: GeminiAPI instance
        company_domain: Company domain (e.g., "example.com")
    
    Returns:
        dict: Parsed company profile JSON
    """
    logger.info(f"Generating company profile for domain: {company_domain}")
    
    # Load the company profile prompt template
    template = load_prompt_template("company_profile.md")
    
    # Create the search query
    search_query = f"""
Please analyze the company at domain {company_domain} and generate a comprehensive company profile.

Use Web Search Grounding to:
1. Find website content about the company
2. Find LinkedIn company information
3. Research competitors in the market
4. Validate market position and offerings

Then generate the JSON profile according to the OUTPUT_STRUCTURE.

Company Domain: {company_domain}

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
        
        # Clean up markdown formatting if present
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        profile = json.loads(cleaned_response)
        logger.info(f"Successfully generated profile for {company_domain}")
        return profile
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse company profile JSON: {e}")
        logger.error(f"Response was: {response}")
        raise
    except Exception as e:
        logger.error(f"Error generating company profile: {e}")
        raise


def generate_solutions_profile(gemini_api: GeminiAPI, company_domain: str, company_profile: dict) -> list:
    """
    Generate solutions profile based on company profile.
    
    Args:
        gemini_api: GeminiAPI instance
        company_domain: Company domain
        company_profile: Company profile dict from generate_company_profile
    
    Returns:
        list: Parsed solutions profile JSON array
    """
    logger.info(f"Generating solutions profile for {company_domain}")
    
    # Load the solutions profile prompt template
    template = load_prompt_template("solutions_profile.md")
    
    # Convert company profile to formatted string
    company_profile_str = json.dumps(company_profile, indent=2)
    
    # Create the search query
    search_query = f"""
Please analyze the solutions provided by {company_domain} based on the following company profile and their website content.

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
        
        # Clean up markdown formatting if present
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        solutions = json.loads(cleaned_response)
        logger.info(f"Successfully generated {len(solutions)} solution profiles")
        return solutions
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse solutions profile JSON: {e}")
        logger.error(f"Response was: {response}")
        raise
    except Exception as e:
        logger.error(f"Error generating solutions profile: {e}")
        raise


def save_results(company_domain: str, company_profile: dict, solutions_profile: list, output_dir: Path = None) -> tuple:
    """
    Save the results to JSON files.
    
    Args:
        company_domain: Company domain
        company_profile: Company profile dict
        solutions_profile: Solutions profile list
        output_dir: Directory to save results (defaults to workspace root)
    
    Returns:
        tuple: (profile_output_path, solutions_output_path)
    """
    if output_dir is None:
        output_dir = WORKSPACE_ROOT / "output"
    
    output_dir.mkdir(exist_ok=True)
    
    # Create sanitized domain name for filenames
    domain_name = company_domain.replace(".", "_").replace("/", "_")
    
    # Save company profile
    profile_path = output_dir / f"{domain_name}_company_profile.json"
    with open(profile_path, 'w', encoding='utf-8') as f:
        json.dump(company_profile, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved company profile to: {profile_path}")
    
    # Save solutions profile
    solutions_path = output_dir / f"{domain_name}_solutions_profile.json"
    with open(solutions_path, 'w', encoding='utf-8') as f:
        json.dump(solutions_profile, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved solutions profile to: {solutions_path}")
    
    return profile_path, solutions_path


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate company profile and solutions analysis using Gemini API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_company_solutions.py example.com
  python generate_company_solutions.py stripe.com --output ./results
        """
    )
    
    parser.add_argument(
        "domain",
        help="Company domain (e.g., example.com or https://example.com)"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for results (default: ./output)"
    )
    
    parser.add_argument(
        "--model",
        default="gemini-2.5-pro",
        help="Gemini model to use (default: gemini-2.5-pro)"
    )
    
    args = parser.parse_args()
    
    # Clean up domain input
    domain = args.domain.lower()
    if domain.startswith("http://"):
        domain = domain[7:]
    if domain.startswith("https://"):
        domain = domain[8:]
    if domain.endswith("/"):
        domain = domain[:-1]
    
    logger.info(f"Starting analysis for domain: {domain}")
    
    try:
        # Initialize Gemini API
        gemini_api = GeminiAPI(model_id=args.model)
        logger.info(f"Initialized Gemini API with model: {args.model}")
        
        # Step 1: Generate company profile
        company_profile = generate_company_profile(gemini_api, domain)
        
        # Step 2: Generate solutions profile
        solutions_profile = generate_solutions_profile(gemini_api, domain, company_profile)
        
        # Step 3: Save results
        profile_path, solutions_path = save_results(domain, company_profile, solutions_profile, args.output)
        
        logger.info("Analysis complete!")
        logger.info(f"Company profile: {profile_path}")
        logger.info(f"Solutions profile: {solutions_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        print(f"Domain: {domain}")
        print(f"Company Name: {company_profile.get('name', 'N/A')}")
        print(f"Industry: {company_profile.get('core_business', {}).get('industry', 'N/A')}")
        print(f"Company Size: {company_profile.get('core_business', {}).get('company_size', 'N/A')}")
        print(f"Solutions Found: {len(solutions_profile)}")
        
        if solutions_profile:
            print("\nSolutions:")
            for i, solution in enumerate(solutions_profile, 1):
                print(f"  {i}. {solution.get('Title', 'N/A')}")
        
        print(f"\nProfile saved to: {profile_path}")
        print(f"Solutions saved to: {solutions_path}")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
