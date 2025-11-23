"""
Parallel Competitor Enrichment Functions

Simple functions for enriching competitor profiles using Google Search grounding
via Gemini API. No complex orchestrator - just clean async functions.

Usage:
    # Single competitor
    result = await enrich_single_competitor(competitor, company, db)

    # All competitors in parallel
    results = await enrich_all_competitors(company_domain, db)
"""

import asyncio
import logging
import json
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pathlib import Path

from db_models import Company, Competitor
from api_clients.gemini_adapter import GeminiAPI
from schemas import CompetitorProfile

logger = logging.getLogger(__name__)


def _load_prompt_template() -> str:
    """Load the competitor enrichment prompt template."""
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_path = prompts_dir / "solutions_competitors_profile.md"

    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def _parse_json_response(response: str, competitor_domain: str) -> Dict[str, Any]:
    """Parse JSON from Gemini response, handling markdown code blocks."""
    try:
        cleaned_response = response.strip()

        # Handle markdown code blocks
        if "```json" in cleaned_response:
            start_marker = "```json"
            end_marker = "```"

            start_idx = cleaned_response.find(start_marker)
            if start_idx != -1:
                start_idx += len(start_marker)
                end_idx = cleaned_response.find(end_marker, start_idx)
                if end_idx != -1:
                    cleaned_response = cleaned_response[start_idx:end_idx]
                else:
                    cleaned_response = cleaned_response[start_idx:]

        cleaned_response = cleaned_response.strip()
        return json.loads(cleaned_response)

    except json.JSONDecodeError as e:
        logger.error(f"[{competitor_domain}] Failed to parse JSON: {e}")
        logger.error(f"[{competitor_domain}] Response was: {response[:500]}...")
        raise ValueError(f"Invalid JSON response for {competitor_domain}")


def _ensure_competitors_in_db(company: Company, db: Session) -> List[Competitor]:
    """
    Ensure competitors from company.profile are in the Competitor table.

    Args:
        company: Company instance
        db: Database session

    Returns:
        List of Competitor instances
    """
    if not company.profile or "competitors" not in company.profile:
        logger.warning(f"No competitors found in company profile for {company.domain}")
        return []

    competitors_data = company.profile.get("competitors", [])
    competitor_records = []

    for comp_data in competitors_data:
        # Extract domain from competitor data
        domain = comp_data.get("domain", comp_data.get("website", ""))
        if not domain:
            logger.warning(f"Skipping competitor with no domain: {comp_data}")
            continue

        # Clean domain
        domain = domain.replace("http://", "").replace("https://", "").replace("www.", "").strip("/")

        # Check if competitor already exists
        existing = db.query(Competitor).filter_by(
            company_id=company.id,
            domain=domain
        ).first()

        if existing:
            logger.info(f"Competitor {domain} already exists")
            competitor_records.append(existing)
        else:
            # Create new competitor record
            new_competitor = Competitor(
                company_id=company.id,
                domain=domain,
                solutions={}  # Will be enriched later
            )
            db.add(new_competitor)
            logger.info(f"Created new competitor record: {domain}")
            competitor_records.append(new_competitor)

    # Commit to save new competitors
    db.commit()

    logger.info(f"Ensured {len(competitor_records)} competitors in database")
    return competitor_records


async def enrich_single_competitor(
    competitor_id: int,
    competitor_domain: str,
    company_profile: dict,
    company_solutions: list,
    db: Session
) -> Dict[str, Any]:
    """
    Enrich a single competitor using Gemini with Google Search grounding.

    Args:
        competitor_id: Database ID of competitor
        competitor_domain: Competitor domain
        company_profile: Company profile dict (for context)
        company_solutions: Company solutions list (for context)
        db: Database session

    Returns:
        Dict with:
            - competitor_domain: str
            - competitor_id: int
            - success: bool
            - data: Dict (enriched profile if successful)
            - error: str (if failed)
    """
    try:
        logger.info(f"[{competitor_domain}] Starting enrichment")

        # Load prompt template
        prompt_template = _load_prompt_template()

        # Build company context
        company_profile_json = json.dumps(company_profile, indent=2) if company_profile else "{}"
        solutions_profile_json = json.dumps(company_solutions, indent=2) if company_solutions else "[]"

        # Fetch competitor's existing data from DB
        competitor = db.query(Competitor).filter_by(id=competitor_id).first()
        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found")

        competitor_existing_data = json.dumps(competitor.solutions, indent=2) if competitor.solutions else "{}"

        # Format prompt with variable substitution
        formatted_prompt = prompt_template.replace("{company_profile}", company_profile_json) \
                                          .replace("{solutions_profile}", solutions_profile_json) \
                                          .replace("{competitor_domain}", competitor_domain) \
                                          .replace("{competitor_existing_data}", competitor_existing_data)

        logger.info(f"[{competitor_domain}] Calling Gemini API with Google Search")

        # Call Gemini API with the formatted prompt
        gemini_api = GeminiAPI(model_id="gemini-3-pro-preview")

        response = await asyncio.to_thread(
            gemini_api.get_google_search_response,
            prompt=formatted_prompt,
            model_name="gemini-3-pro-preview",
            thinking_budget=8000,
            temperature=0.7
        )

        logger.info(f"[{competitor_domain}] Received response")

        # Parse JSON
        enriched_profile = _parse_json_response(response, competitor_domain)

        # Re-fetch competitor and update (avoid session issues)
        competitor = db.query(Competitor).filter_by(id=competitor_id).first()
        if competitor:
            competitor.solutions = enriched_profile
            db.commit()
            logger.info(f"[{competitor_domain}] ✓ Enrichment successful")
        else:
            raise ValueError(f"Competitor {competitor_id} disappeared during enrichment")

        return {
            "competitor_domain": competitor_domain,
            "competitor_id": competitor_id,
            "success": True,
            "data": enriched_profile
        }

    except Exception as e:
        logger.error(f"[{competitor_domain}] ✗ Enrichment failed: {e}", exc_info=True)
        db.rollback()

        return {
            "competitor_domain": competitor_domain,
            "competitor_id": competitor_id,
            "success": False,
            "error": str(e)
        }


async def enrich_all_competitors(
    company_domain: str,
    db: Session,
    max_concurrent: int = 3
) -> Dict[str, Any]:
    """
    Enrich all competitors for a company in parallel using asyncio.gather.

    Args:
        company_domain: Company domain
        db: Database session
        max_concurrent: Maximum concurrent enrichments (default: 3)

    Returns:
        Dict with:
            - total: int
            - successful: int
            - failed: int
            - results: List[Dict]
            - execution_time_seconds: float
            - company_name: str
    """
    start_time = datetime.utcnow()

    logger.info("=" * 80)
    logger.info(f"Starting competitor enrichment for: {company_domain}")
    logger.info("=" * 80)

    # Fetch company
    company = db.query(Company).filter_by(domain=company_domain).first()
    if not company:
        raise ValueError(f"Company not found: {company_domain}")

    # Ensure competitors from profile are in database
    competitors = _ensure_competitors_in_db(company, db)

    if not competitors:
        logger.warning(f"No competitors found for {company_domain}")
        return {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "results": [],
            "execution_time_seconds": 0,
            "company_name": company.profile.get("name", company_domain) if company.profile else company_domain
        }

    logger.info(f"Found {len(competitors)} competitors to enrich")

    # Extract company context once (avoid passing ORM objects to async tasks)
    company_profile = company.profile or {}
    company_solutions = company.solutions or []

    # Build list of competitor info (ID + domain only, no ORM objects)
    competitor_info = [(comp.id, comp.domain) for comp in competitors]

    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(max_concurrent)

    async def enrich_with_semaphore(comp_id, comp_domain):
        """Wrapper to apply semaphore rate limiting."""
        async with semaphore:
            return await enrich_single_competitor(
                competitor_id=comp_id,
                competitor_domain=comp_domain,
                company_profile=company_profile,
                company_solutions=company_solutions,
                db=db
            )

    # Launch all tasks in parallel with gather
    tasks = [enrich_with_semaphore(comp_id, comp_domain) for comp_id, comp_domain in competitor_info]

    logger.info(f"Launching {len(tasks)} parallel tasks (max concurrent: {max_concurrent})")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    successful = []
    failed = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            _, comp_domain = competitor_info[i]
            logger.error(f"Task failed for {comp_domain}: {result}")
            failed.append({
                "competitor_domain": comp_domain,
                "success": False,
                "error": str(result)
            })
        elif result.get("success"):
            successful.append(result)
        else:
            failed.append(result)

    # Calculate execution time
    end_time = datetime.utcnow()
    execution_time = (end_time - start_time).total_seconds()

    # Build summary
    summary = {
        "total": len(competitors),
        "successful": len(successful),
        "failed": len(failed),
        "results": successful + failed,
        "execution_time_seconds": execution_time,
        "company_name": company_profile.get("name", company_domain)
    }

    logger.info("=" * 80)
    logger.info(f"Enrichment complete: {summary['successful']}/{summary['total']} successful")
    logger.info(f"Execution time: {execution_time:.2f}s")
    logger.info("=" * 80)

    return summary