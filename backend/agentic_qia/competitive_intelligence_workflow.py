"""
Multi-Agent Competitive Intelligence Workflow using ReactGraph

This module orchestrates multiple ReactGraph instances to perform comprehensive
competitive intelligence analysis:

1. Company Research Agent - Analyzes target company
2. Competitor Discovery Agent - Identifies main competitors
3. Per-Competitor Agents (parallel):
   - Product Analysis Agent
   - Product Comparison Agent
   - Customer Reviews Agent
   - Strategy Analysis Agent
   - News Monitoring Agent
4. Aggregator Agent - Synthesizes all findings into comprehensive report
5. Alert System Agent - Identifies critical competitive threats

Author: Competitive Intelligence Platform
"""

from typing import Dict, Any, List, Optional, Tuple
from .graph import ReactGraph
import logging
import asyncio
import json
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class CompetitorAnalysisResult:
    """Container for competitor analysis results"""

    def __init__(self, competitor_name: str, competitor_domain: str):
        self.competitor_name = competitor_name
        self.competitor_domain = competitor_domain
        self.products_analysis = None
        self.product_comparison = None
        self.customer_reviews = None
        self.strategy_analysis = None
        self.news_monitoring = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for aggregation"""
        return {
            "competitor_name": self.competitor_name,
            "competitor_domain": self.competitor_domain,
            "products_analysis": self.products_analysis,
            "product_comparison": self.product_comparison,
            "customer_reviews": self.customer_reviews,
            "strategy_analysis": self.strategy_analysis,
            "news_monitoring": self.news_monitoring
        }


class MultiAgentCompetitiveIntelligence:
    """
    Orchestrates multiple ReactGraph instances for comprehensive competitive intelligence.

    Workflow:
    1. Company Research: Analyze target company (products, domains, strategies)
    2. Competitor Discovery: Identify main competitors
    3. Per-Competitor Analysis (parallel):
       - Products analysis
       - Product comparison vs our products
       - Customer reviews
       - Strategy analysis
       - News monitoring
    4. Aggregation: Create comprehensive comparison report
    5. Alerts: Generate critical threat alerts
    """

    def __init__(self,
                 company_name: str,
                 company_domain: str,
                 company_industry: str = "",
                 company_size: str = "",
                 max_competitors: int = 5):
        """
        Initialize Multi-Agent Competitive Intelligence Workflow

        Args:
            company_name: Target company name
            company_domain: Target company domain
            company_industry: Industry/sector
            company_size: Company size (employees/revenue)
            max_competitors: Maximum number of competitors to analyze
        """
        self.company_name = company_name
        self.company_domain = company_domain
        self.company_industry = company_industry
        self.company_size = company_size
        self.max_competitors = max_competitors

        # Results storage
        self.company_research_result = None
        self.competitors_discovered = []
        self.competitor_analyses = {}
        self.final_report = None
        self.alerts = None

        # Prompts directory
        self.prompts_dir = os.path.join(
            os.path.dirname(__file__),
            "prompts",
            "competitive_intelligence"
        )

        logger.info(f"Initialized MultiAgentCompetitiveIntelligence for {company_name}")

    def _load_prompt(self, prompt_name: str) -> str:
        """Load prompt from file"""
        prompt_path = os.path.join(self.prompts_dir, f"{prompt_name}.md")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_path}")
            raise

    def _create_company_context(self,
                                company_name: str = None,
                                company_domain: str = None,
                                industry: str = None,
                                size: str = None) -> Dict[str, Any]:
        """Create company context dict for ReactGraph"""
        return {
            "name": company_name or self.company_name,
            "domain": company_domain or self.company_domain,
            "industry": industry or self.company_industry,
            "size": size or self.company_size
        }

    async def step1_company_research(self) -> Dict[str, Any]:
        """
        Step 1: Research target company

        Analyzes:
        - Business domains and activities
        - Products and services
        - Business strategies
        - Market positioning

        Returns:
            Company research results
        """
        logger.info("=" * 80)
        logger.info("STEP 1: COMPANY RESEARCH")
        logger.info("=" * 80)

        # Create company context
        company_context = self._create_company_context()

        # Create datapoint context for company research
        datapoint_context = {
            "dp_name": "Company_Research_Analysis",
            "description": "Comprehensive analysis of target company including business domains, products, and strategies",
            "value_ranges": {}
        }

        # Initialize ReactGraph
        agent = ReactGraph(
            company_context=company_context,
            datapoint_context=datapoint_context
        )

        # Load and format prompt
        prompt_template = self._load_prompt("01_company_research")
        prompt = prompt_template.replace("{{company_name}}", self.company_name) \
                                .replace("{{company_domain}}", self.company_domain) \
                                .replace("{{company_industry}}", self.company_industry)

        # Run agent
        logger.info(f"Researching company: {self.company_name}")
        result = await agent.ainvoke(prompt=prompt)

        # Extract structured response
        self.company_research_result = ReactGraph.serialize_response(result)

        logger.info(f"Company research completed. Confidence: {self.company_research_result.get('confidence', 0):.2%}")

        return self.company_research_result

    async def step2_competitor_discovery(self) -> List[Dict[str, str]]:
        """
        Step 2: Discover main competitors

        Uses company research results to identify main competitors.

        Returns:
            List of competitors with name and domain
        """
        logger.info("=" * 80)
        logger.info("STEP 2: COMPETITOR DISCOVERY")
        logger.info("=" * 80)

        # Create company context
        company_context = self._create_company_context()

        # Create datapoint context for competitor discovery
        datapoint_context = {
            "dp_name": "Competitor_Discovery",
            "description": f"Identify top {self.max_competitors} main competitors for {self.company_name}",
            "value_ranges": {}
        }

        # Initialize ReactGraph
        agent = ReactGraph(
            company_context=company_context,
            datapoint_context=datapoint_context
        )

        # Load and format prompt
        prompt_template = self._load_prompt("02_competitor_discovery")

        # Include company research findings
        company_research_summary = self.company_research_result.get('answer', 'No prior research available')

        prompt = prompt_template.replace("{{company_name}}", self.company_name) \
                                .replace("{{company_domain}}", self.company_domain) \
                                .replace("{{company_industry}}", self.company_industry) \
                                .replace("{{max_competitors}}", str(self.max_competitors)) \
                                .replace("{{company_research_summary}}", company_research_summary)

        # Run agent
        logger.info(f"Discovering competitors for {self.company_name}")
        result = await agent.ainvoke(prompt=prompt)

        # Extract structured response
        competitor_discovery_result = ReactGraph.serialize_response(result)

        # Parse competitors from answer (assuming format: "1. CompanyName (domain.com)")
        # This is a simplified parser - in production you'd use structured output
        answer = competitor_discovery_result.get('answer', '')
        competitors = self._parse_competitors_from_text(answer)

        self.competitors_discovered = competitors[:self.max_competitors]

        logger.info(f"Discovered {len(self.competitors_discovered)} competitors: {[c['name'] for c in self.competitors_discovered]}")

        return self.competitors_discovered

    def _parse_competitors_from_text(self, text: str) -> List[Dict[str, str]]:
        """
        Parse competitors from text response

        Expected format examples:
        - "1. Competitor Name (competitor.com)"
        - "Competitor Name - competitor.com"

        Returns:
            List of {name, domain} dicts
        """
        competitors = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to extract name and domain
            # Pattern 1: "1. Name (domain.com)"
            if '(' in line and ')' in line:
                parts = line.split('(')
                if len(parts) >= 2:
                    name = parts[0].strip().lstrip('0123456789.- ')
                    domain = parts[1].split(')')[0].strip()

                    if name and domain:
                        competitors.append({
                            "name": name,
                            "domain": domain
                        })

        # If no competitors found with pattern, try simple extraction
        if not competitors:
            logger.warning("No competitors found with standard pattern, using fallback extraction")
            # Fallback: just use domains mentioned in citations
            import re
            domains = re.findall(r'[\w\-]+\.[\w\-]+\.?[\w]*', text)
            for domain in domains[:self.max_competitors]:
                competitors.append({
                    "name": domain.split('.')[0].title(),
                    "domain": domain
                })

        return competitors

    async def step3_analyze_competitor(self,
                                      competitor: Dict[str, str]) -> CompetitorAnalysisResult:
        """
        Step 3: Analyze single competitor (runs 5 parallel agents)

        Args:
            competitor: Dict with 'name' and 'domain'

        Returns:
            CompetitorAnalysisResult with all analyses
        """
        competitor_name = competitor['name']
        competitor_domain = competitor['domain']

        logger.info("=" * 80)
        logger.info(f"STEP 3: ANALYZING COMPETITOR - {competitor_name}")
        logger.info("=" * 80)

        result = CompetitorAnalysisResult(competitor_name, competitor_domain)

        # Run 5 agents in parallel
        tasks = [
            self._analyze_competitor_products(competitor),
            self._compare_products(competitor),
            self._analyze_customer_reviews(competitor),
            self._analyze_strategy(competitor),
            self._monitor_news(competitor)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assign results
        result.products_analysis = results[0] if not isinstance(results[0], Exception) else None
        result.product_comparison = results[1] if not isinstance(results[1], Exception) else None
        result.customer_reviews = results[2] if not isinstance(results[2], Exception) else None
        result.strategy_analysis = results[3] if not isinstance(results[3], Exception) else None
        result.news_monitoring = results[4] if not isinstance(results[4], Exception) else None

        # Log any errors
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Competitor analysis task {i} failed: {res}")

        logger.info(f"Completed analysis for {competitor_name}")

        return result

    async def _analyze_competitor_products(self, competitor: Dict[str, str]) -> Dict[str, Any]:
        """Analyze competitor's products"""
        logger.info(f"[{competitor['name']}] Analyzing products...")

        company_context = self._create_company_context(
            company_name=competitor['name'],
            company_domain=competitor['domain']
        )

        datapoint_context = {
            "dp_name": "Competitor_Products_Analysis",
            "description": f"Detailed analysis of {competitor['name']}'s products and services",
            "value_ranges": {}
        }

        agent = ReactGraph(company_context, datapoint_context)

        prompt_template = self._load_prompt("03_competitor_products")
        prompt = prompt_template.replace("{{competitor_name}}", competitor['name']) \
                                .replace("{{competitor_domain}}", competitor['domain'])

        result = await agent.ainvoke(prompt=prompt)

        return ReactGraph.serialize_response(result)

    async def _compare_products(self, competitor: Dict[str, str]) -> Dict[str, Any]:
        """Compare our products vs competitor's products"""
        logger.info(f"[{competitor['name']}] Comparing products...")

        company_context = self._create_company_context()

        datapoint_context = {
            "dp_name": "Product_Comparison_Analysis",
            "description": f"Detailed comparison between {self.company_name} and {competitor['name']} products",
            "value_ranges": {}
        }

        agent = ReactGraph(company_context, datapoint_context)

        prompt_template = self._load_prompt("04_product_comparison")

        # Include our company's products from research
        our_products_summary = self.company_research_result.get('answer', 'Unknown products')

        prompt = prompt_template.replace("{{our_company_name}}", self.company_name) \
                                .replace("{{our_company_domain}}", self.company_domain) \
                                .replace("{{competitor_name}}", competitor['name']) \
                                .replace("{{competitor_domain}}", competitor['domain']) \
                                .replace("{{our_products_summary}}", our_products_summary)

        result = await agent.ainvoke(prompt=prompt)

        return ReactGraph.serialize_response(result)

    async def _analyze_customer_reviews(self, competitor: Dict[str, str]) -> Dict[str, Any]:
        """Analyze customer reviews for competitor's products"""
        logger.info(f"[{competitor['name']}] Analyzing customer reviews...")

        company_context = self._create_company_context(
            company_name=competitor['name'],
            company_domain=competitor['domain']
        )

        datapoint_context = {
            "dp_name": "Customer_Reviews_Analysis",
            "description": f"Customer reviews and sentiment analysis for {competitor['name']}'s products",
            "value_ranges": {}
        }

        agent = ReactGraph(company_context, datapoint_context)

        prompt_template = self._load_prompt("05_customer_reviews")
        prompt = prompt_template.replace("{{competitor_name}}", competitor['name']) \
                                .replace("{{competitor_domain}}", competitor['domain'])

        result = await agent.ainvoke(prompt=prompt)

        return ReactGraph.serialize_response(result)

    async def _analyze_strategy(self, competitor: Dict[str, str]) -> Dict[str, Any]:
        """Analyze competitor's business strategy"""
        logger.info(f"[{competitor['name']}] Analyzing strategy...")

        company_context = self._create_company_context(
            company_name=competitor['name'],
            company_domain=competitor['domain']
        )

        datapoint_context = {
            "dp_name": "Strategy_Analysis",
            "description": f"Business strategy analysis for {competitor['name']}",
            "value_ranges": {}
        }

        agent = ReactGraph(company_context, datapoint_context)

        prompt_template = self._load_prompt("06_strategy_analysis")
        prompt = prompt_template.replace("{{competitor_name}}", competitor['name']) \
                                .replace("{{competitor_domain}}", competitor['domain'])

        result = await agent.ainvoke(prompt=prompt)

        return ReactGraph.serialize_response(result)

    async def _monitor_news(self, competitor: Dict[str, str]) -> Dict[str, Any]:
        """Monitor recent news about competitor"""
        logger.info(f"[{competitor['name']}] Monitoring news...")

        company_context = self._create_company_context(
            company_name=competitor['name'],
            company_domain=competitor['domain']
        )

        datapoint_context = {
            "dp_name": "News_Monitoring",
            "description": f"Recent news and developments about {competitor['name']}",
            "value_ranges": {}
        }

        agent = ReactGraph(company_context, datapoint_context)

        prompt_template = self._load_prompt("07_news_monitoring")
        prompt = prompt_template.replace("{{competitor_name}}", competitor['name']) \
                                .replace("{{competitor_domain}}", competitor['domain'])

        result = await agent.ainvoke(prompt=prompt)

        return ReactGraph.serialize_response(result)

    async def step4_aggregate_and_report(self) -> Dict[str, Any]:
        """
        Step 4: Aggregate all competitor analyses into comprehensive report

        Returns:
            Final comprehensive comparison report
        """
        logger.info("=" * 80)
        logger.info("STEP 4: AGGREGATING RESULTS & GENERATING REPORT")
        logger.info("=" * 80)

        company_context = self._create_company_context()

        datapoint_context = {
            "dp_name": "Competitive_Intelligence_Report",
            "description": f"Comprehensive competitive intelligence report for {self.company_name}",
            "value_ranges": {}
        }

        agent = ReactGraph(company_context, datapoint_context)

        prompt_template = self._load_prompt("08_aggregation_report")

        # Serialize all competitor analyses
        competitors_data = []
        for comp_name, analysis in self.competitor_analyses.items():
            competitors_data.append(analysis.to_dict())

        competitors_json = json.dumps(competitors_data, indent=2, ensure_ascii=False)
        company_research_json = json.dumps(self.company_research_result, indent=2, ensure_ascii=False)

        prompt = prompt_template.replace("{{our_company_name}}", self.company_name) \
                                .replace("{{our_company_domain}}", self.company_domain) \
                                .replace("{{company_research_data}}", company_research_json) \
                                .replace("{{competitors_data}}", competitors_json)

        logger.info("Generating comprehensive competitive intelligence report...")
        result = await agent.ainvoke(prompt=prompt)

        self.final_report = ReactGraph.serialize_response(result)

        logger.info("Comprehensive report generated successfully")

        return self.final_report

    async def step5_generate_alerts(self) -> Dict[str, Any]:
        """
        Step 5: Generate critical threat alerts

        Analyzes all competitor data to identify critical competitive threats
        that require immediate attention.

        Returns:
            Alert analysis with priority threats
        """
        logger.info("=" * 80)
        logger.info("STEP 5: GENERATING COMPETITIVE THREAT ALERTS")
        logger.info("=" * 80)

        company_context = self._create_company_context()

        datapoint_context = {
            "dp_name": "Competitive_Threat_Alerts",
            "description": f"Critical competitive threat alerts for {self.company_name}",
            "value_ranges": {}
        }

        agent = ReactGraph(company_context, datapoint_context)

        prompt_template = self._load_prompt("09_alert_system")

        # Serialize all competitor analyses
        competitors_data = []
        for comp_name, analysis in self.competitor_analyses.items():
            competitors_data.append(analysis.to_dict())

        competitors_json = json.dumps(competitors_data, indent=2, ensure_ascii=False)
        company_research_json = json.dumps(self.company_research_result, indent=2, ensure_ascii=False)

        prompt = prompt_template.replace("{{our_company_name}}", self.company_name) \
                                .replace("{{our_company_domain}}", self.company_domain) \
                                .replace("{{company_research_data}}", company_research_json) \
                                .replace("{{competitors_data}}", competitors_json)

        logger.info("Analyzing competitive threats and generating alerts...")
        result = await agent.ainvoke(prompt=prompt)

        self.alerts = ReactGraph.serialize_response(result)

        logger.info("Threat alerts generated successfully")

        return self.alerts

    async def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run complete competitive intelligence workflow

        Returns:
            Complete results including:
            - company_research
            - competitors_discovered
            - competitor_analyses
            - final_report
            - alerts
        """
        logger.info("=" * 80)
        logger.info(f"STARTING FULL COMPETITIVE INTELLIGENCE ANALYSIS FOR {self.company_name}")
        logger.info("=" * 80)

        start_time = datetime.now()

        try:
            # Step 1: Research our company
            await self.step1_company_research()

            # Step 2: Discover competitors
            await self.step2_competitor_discovery()

            # Step 3: Analyze each competitor (parallel)
            competitor_tasks = [
                self.step3_analyze_competitor(competitor)
                for competitor in self.competitors_discovered
            ]

            competitor_results = await asyncio.gather(*competitor_tasks, return_exceptions=True)

            # Store results
            for i, result in enumerate(competitor_results):
                if not isinstance(result, Exception):
                    competitor_name = self.competitors_discovered[i]['name']
                    self.competitor_analyses[competitor_name] = result
                else:
                    logger.error(f"Failed to analyze competitor {i}: {result}")

            # Step 4: Aggregate and generate report
            await self.step4_aggregate_and_report()

            # Step 5: Generate alerts
            await self.step5_generate_alerts()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info("=" * 80)
            logger.info(f"COMPETITIVE INTELLIGENCE ANALYSIS COMPLETED in {duration:.1f}s")
            logger.info("=" * 80)

            return {
                "company_research": self.company_research_result,
                "competitors_discovered": self.competitors_discovered,
                "competitor_analyses": {
                    name: analysis.to_dict()
                    for name, analysis in self.competitor_analyses.items()
                },
                "final_report": self.final_report,
                "alerts": self.alerts,
                "metadata": {
                    "company_name": self.company_name,
                    "company_domain": self.company_domain,
                    "analysis_date": start_time.isoformat(),
                    "duration_seconds": duration,
                    "num_competitors_analyzed": len(self.competitor_analyses)
                }
            }

        except Exception as e:
            logger.error(f"Competitive intelligence analysis failed: {e}", exc_info=True)
            raise


# Example usage
async def main():
    """Example usage of MultiAgentCompetitiveIntelligence"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize workflow
    workflow = MultiAgentCompetitiveIntelligence(
        company_name="UiPath",
        company_domain="uipath.com",
        company_industry="Robotic Process Automation (RPA)",
        company_size="~4000 employees",
        max_competitors=3
    )

    # Run full analysis
    results = await workflow.run_full_analysis()

    # Save results to file
    output_file = f"competitive_intelligence_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {output_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("COMPETITIVE INTELLIGENCE ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"\nCompany: {results['metadata']['company_name']}")
    print(f"Competitors Analyzed: {results['metadata']['num_competitors_analyzed']}")
    print(f"Duration: {results['metadata']['duration_seconds']:.1f}s")
    print("\nCompetitors:")
    for comp in results['competitors_discovered']:
        print(f"  - {comp['name']} ({comp['domain']})")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
