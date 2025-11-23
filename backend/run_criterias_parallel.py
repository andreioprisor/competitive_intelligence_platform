"""
Parallel Criteria Analysis Orchestrator

This module orchestrates parallel execution of ReactGraph agents for analyzing
multiple competitors against a single criteria. Results are cached in the database.

Usage:
    orchestrator = CriteriaAnalysisOrchestrator(max_concurrency=3, db_session=db)
    results = await orchestrator.run_criteria_for_all_competitors(
        company_domain="example.com",
        criteria_id=123
    )
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db_models import Company, Competitor, Criteria, Value
from agentic_qia.graph import ReactGraph

logger = logging.getLogger(__name__)


class CriteriaAnalysisOrchestrator:
    """
    Orchestrates parallel execution of ReactGraph agents for competitor analysis.

    This class manages:
    - Concurrent execution with configurable limits
    - Database integration for fetching and caching
    - Error handling and logging
    - Result aggregation
    """

    def __init__(self, max_concurrency: int = 3, db_session: Session = None):
        """
        Initialize the orchestrator.

        Args:
            max_concurrency: Maximum number of concurrent agent executions
            db_session: SQLAlchemy database session
        """
        self.max_concurrency = max_concurrency
        self.db = db_session

        if not self.db:
            raise ValueError("Database session is required")

        logger.info(f"Initialized CriteriaAnalysisOrchestrator with max_concurrency={max_concurrency}")

    async def run_criteria_for_all_competitors(
        self,
        company_domain: str,
        criteria_id: int
    ) -> Dict[str, Any]:
        """
        Run criteria analysis for all competitors of a company in parallel.

        This method:
        1. Fetches company, competitors, and criteria from database
        2. Creates ReactGraph agent for each competitor
        3. Runs agents in parallel with concurrency control
        4. Caches results in Value table
        5. Returns aggregated results

        Args:
            company_domain: Company domain to analyze competitors for
            criteria_id: ID of the criteria to analyze

        Returns:
            Dict containing:
                - total: Total number of competitors
                - successful: Number of successful analyses
                - failed: Number of failed analyses
                - results: List of individual results
                - execution_time_seconds: Total execution time
                - company_name: Name of the company
                - criteria_name: Name of the criteria

        Raises:
            ValueError: If company or criteria not found
        """
        start_time = datetime.utcnow()

        logger.info("=" * 80)
        logger.info(f"Starting criteria analysis for company: {company_domain}")
        logger.info(f"Criteria ID: {criteria_id}")
        logger.info("=" * 80)

        # Step 1: Fetch company
        company = self.db.query(Company).filter_by(domain=company_domain).first()
        if not company:
            raise ValueError(f"Company not found for domain: {company_domain}")

        # Step 2: Fetch competitors
        competitors = company.competitors
        if not competitors:
            logger.warning(f"No competitors found for company: {company_domain}")
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
                "execution_time_seconds": 0,
                "company_name": company.profile.get("name", company_domain),
                "criteria_name": "N/A"
            }

        # Step 3: Fetch criteria
        criteria = self.db.query(Criteria).filter_by(id=criteria_id).first()
        if not criteria:
            raise ValueError(f"Criteria not found for ID: {criteria_id}")

        logger.info(f"Found {len(competitors)} competitors to analyze")
        logger.info(f"Criteria: {criteria.name}")

        # Step 4: Build company context
        company_context = {
            "name": company.profile.get("name", company_domain),
            "domain": company.domain,
            "industry": company.profile.get("core_business", {}).get("industry", "Unknown"),
            "size": company.profile.get("company_size", "Unknown")
        }

        # Step 5: Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrency)

        # Step 6: Launch parallel tasks
        tasks = [
            self._analyze_single_competitor(
                competitor=competitor,
                criteria=criteria,
                company_context=company_context,
                semaphore=semaphore
            )
            for competitor in competitors
        ]

        logger.info(f"Launching {len(tasks)} parallel analysis tasks (max concurrency: {self.max_concurrency})")

        # Step 7: Execute all tasks (continue on failures)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Step 8: Process results
        successful_results = []
        failed_results = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                competitor_domain = competitors[i].domain
                logger.error(f"Analysis failed for competitor {competitor_domain}: {result}")
                failed_results.append({
                    "competitor_domain": competitor_domain,
                    "success": False,
                    "error": str(result)
                })
            elif result and result.get("success"):
                successful_results.append(result)
            else:
                failed_results.append(result)

        # Step 9: Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()

        # Step 10: Build summary
        summary = {
            "total": len(competitors),
            "successful": len(successful_results),
            "failed": len(failed_results),
            "results": successful_results + failed_results,
            "execution_time_seconds": execution_time,
            "company_name": company.profile.get("name", company_domain),
            "criteria_name": criteria.name
        }

        logger.info("=" * 80)
        logger.info("Criteria Analysis Complete")
        logger.info(f"Total: {summary['total']}, Successful: {summary['successful']}, Failed: {summary['failed']}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info("=" * 80)

        return summary

    async def _analyze_single_competitor(
        self,
        competitor: Competitor,
        criteria: Criteria,
        company_context: Dict[str, Any],
        semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        """
        Analyze a single competitor against a criteria using ReactGraph.

        This method:
        1. Acquires semaphore for rate limiting
        2. Creates ReactGraph agent with competitor context
        3. Runs agent
        4. Serializes and caches result in Value table
        5. Releases semaphore

        Args:
            competitor: Competitor model instance
            criteria: Criteria model instance
            company_context: Company context dict (for industry/size context)
            semaphore: Asyncio semaphore for concurrency control

        Returns:
            Dict with analysis result:
                - competitor_domain: Competitor domain
                - competitor_id: Database ID
                - success: Whether analysis succeeded
                - data: Serialized analysis result (if successful)
                - error: Error message (if failed)
        """
        competitor_domain = competitor.domain

        async with semaphore:
            try:
                logger.info(f"[{competitor_domain}] Starting analysis for criteria: {criteria.name}")

                # Step 1: Build competitor context
                competitor_context = {
                    "name": competitor.solutions.get("name", competitor_domain) if competitor.solutions else competitor_domain,
                    "domain": competitor.domain,
                    "industry": company_context.get("industry", "Unknown"),
                    "size": competitor.solutions.get("company_size", "Unknown") if competitor.solutions else "Unknown"
                }

                # Step 2: Build datapoint context from criteria
                datapoint_context = {
                    "dp_name": criteria.name,
                    "description": criteria.definition or criteria.name,
                    "value_ranges": {}  # Can be extended to store value_ranges in Criteria table
                }

                logger.info(f"[{competitor_domain}] Initializing ReactGraph agent")

                # Step 3: Initialize ReactGraph agent with proper context separation
                # company_context = YOUR company (for reference)
                # competitor_context = Target competitor (what we're analyzing)
                agent = ReactGraph(
                    company_context=company_context,
                    competitor_context=competitor_context,
                    datapoint_context=datapoint_context
                )

                # Step 4: Run agent
                logger.info(f"[{competitor_domain}] Running ReactGraph analysis...")
                result = await agent.ainvoke(
                    prompt=f"Analyze {criteria.name} for {competitor_domain}. {criteria.definition}"
                )

                # Step 5: Serialize response
                serialized = ReactGraph.serialize_response(result)

                logger.info(f"[{competitor_domain}] Analysis complete. Confidence: {serialized.get('confidence', 0):.2%}")

                # Step 6: Save to database (upsert pattern)
                try:
                    value_record = self.db.query(Value).filter_by(
                        criteria_id=criteria.id,
                        competitor_id=competitor.id
                    ).first()

                    if value_record:
                        logger.info(f"[{competitor_domain}] Updating existing Value record")
                        value_record.value = serialized
                    else:
                        logger.info(f"[{competitor_domain}] Creating new Value record")
                        value_record = Value(
                            criteria_id=criteria.id,
                            competitor_id=competitor.id,
                            value=serialized
                        )
                        self.db.add(value_record)

                    self.db.commit()
                    logger.info(f"[{competitor_domain}] Successfully saved to database")

                except SQLAlchemyError as db_error:
                    self.db.rollback()
                    logger.error(f"[{competitor_domain}] Database error: {db_error}")
                    raise

                # Step 7: Return success result
                return {
                    "competitor_domain": competitor_domain,
                    "competitor_id": competitor.id,
                    "success": True,
                    "data": serialized
                }

            except Exception as e:
                logger.error(f"[{competitor_domain}] Analysis failed: {e}", exc_info=True)

                # Return error result (don't raise - let gather continue)
                return {
                    "competitor_domain": competitor_domain,
                    "competitor_id": competitor.id if competitor else None,
                    "success": False,
                    "error": str(e)
                }
