"""
LangGraph node implementations for agentic QIA

Node Responsibilities:
- Triage: Convert user prompt into structured research plan
- Agent Controller: Wraps LangGraph's create_react_agent with budget enforcement
- Final Synthesis: Create final answer from all collected evidence
"""
import logging
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from .state import AgenticRunState
from .tools import TOOLS, get_tool_cost

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Budget Manager (per thread)
# ------------------------------------------------------------------------------

@dataclass
class Budget:
    queries: int
    pages: int
    seconds: int
    evidence_tokens: int
    ai_overviews: int
    pdf: int
    google_ads: int
    


@dataclass
class Usage:
    queries: int = 0
    pages: int = 0
    seconds: int = 0
    evidence_tokens: int = 0
    ai_overviews: int = 0
    pdf: int = 0
    google_ads: int = 0


@dataclass
class BudgetRecord:
    budget: Budget
    usage: Usage = field(default_factory=Usage)


class BudgetManager:
    """
    In-memory budget tracking keyed by thread_id.
    """
    _store: Dict[str, BudgetRecord] = {}

    @classmethod
    def set_budget(cls, thread_id: str, budget: Budget):
        cls._store[thread_id] = BudgetRecord(budget=budget)

    @classmethod
    def get(cls, thread_id: str) -> BudgetRecord:
        return cls._store[thread_id]

    @classmethod
    def safe_get(cls, thread_id: str) -> Optional[BudgetRecord]:
        return cls._store.get(thread_id)

    @classmethod
    def inc(cls, thread_id: str, **deltas):
        rec = cls.get(thread_id)
        for k, v in deltas.items():
            if hasattr(rec.usage, k):
                setattr(rec.usage, k, getattr(rec.usage, k) + int(v))

    @classmethod
    def check_limits(cls, thread_id: str):
        rec = cls.get(thread_id)
        u, b = rec.usage, rec.budget
        hard_stop = (
            u.queries >= b.queries or
            u.pages >= b.pages or
            u.evidence_tokens >= b.evidence_tokens or
            u.ai_overviews >= b.ai_overviews or
            u.pdf >= b.pdf or
            u.google_ads >= b.google_ads
        )
        if hard_stop:
            raise RuntimeError("Budget exhausted")

logger = logging.getLogger(__name__)

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
AGENT_REASONING_PROMPT = os.path.join(PROMPTS_DIR, "agent_reasoning.md")
TRIAGE_PROMPT = os.path.join(PROMPTS_DIR, "triage.md")

# Reuse synthesis prompt from qia_agent
QIA_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qia_agent", "agentic_prompts")
FINAL_SYNTHESIS_PROMPT = os.path.join(QIA_PROMPTS_DIR, "final_raw_synthesis.md")

def node_triage(state: AgenticRunState) -> Dict[str, Any]:
    """
    Planning node: Convert user prompt to research plan using comprehensive triage prompt

    Uses LLM to generate: goal, instructions, stopping_criteria, obtainability, budget_plan
    """
    from api_clients.open_router import OpenRouterAdapter
    from datetime import datetime
    import json

    try:
        # Format available tools for prompt
        available_tools = state.get("tools_registry")

        # Load and format triage prompt
        datapoint_def = state.get("datapoint_definition", {})
        datapoint_name = datapoint_def.get("dp_name", "")
        definition = datapoint_def.get("description", "") or datapoint_def.get("definition", "")
        value_ranges = datapoint_def.get("value_ranges", "")

        if not datapoint_name or not definition:
            raise ValueError(f"Datapoint definition is missing required fields. Got: {datapoint_def}")

        # Get current date for time-aware planning
        current_datetime = datetime.now().date().isoformat()

        # Load triage prompt template from prompts folder
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "triage.md")
        with open(prompt_path, 'r') as f:
            prompt_template = f.read()

        # Format prompt with variables using simple string replacement
        prompt = prompt_template.replace("{current_datetime}", current_datetime)
        prompt = prompt.replace("{company_context}", json.dumps(state.get("company_context", {}), indent=2))
        prompt = prompt.replace("{competitor_context}", json.dumps(state.get("competitor_context", {}), indent=2) if state.get("competitor_context") else "None")
        prompt = prompt.replace("{datapoint_name}", datapoint_name)
        prompt = prompt.replace("{datapoint_definition}", definition)
        prompt = prompt.replace("{value_ranges}", json.dumps(value_ranges, indent=2) if isinstance(value_ranges, dict) else str(value_ranges))
        prompt = prompt.replace("{available_tools}", json.dumps(available_tools, indent=2) if isinstance(available_tools, dict) else str(available_tools))

        print("Triage prompt:")
        print(prompt)  # DEBUG

        # Use OpenRouterAdapter for LLM call
        adapter = OpenRouterAdapter()
        response_text = adapter.get_completion(
            prompt=prompt + "\n\nRespond with valid JSON only.",
            model="google/gemini-2.5-flash",
            temperature=0.01,
            max_output_tokens=4000
        )

        # Parse JSON response
        result = json.loads(response_text.strip().replace("```json", "").replace("```", ""))

        logger.info(f"Triage result: {result}")
        # Build budgets
        # bp = result["budget_plan"]
        # budgets = {
        #     "max_queries": bp["serp_queries"],
        #     "max_pages": bp["crawled_pages"],
        #     "max_seconds": 60,
        #     "max_evidence_tokens": bp["evidence_tokens"],
        #     "max_ai_overviews": bp["ai_overviews"]
        # }

        # Extract dp_contract from result or build from datapoint_definition
        dp_contract = result.get("dp_contract")
        if not dp_contract:
            # Fallback: build from datapoint_definition if LLM didn't provide it
            datapoint_def = state.get("datapoint_definition", {})
            if datapoint_def.get("dp_name"):
                dp_contract = {
                    "dp_id": datapoint_def.get("dp_name", "").lower().replace(" ", "_"),
                    "dp_name": datapoint_def.get("dp_name"),
                    "value_ranges": datapoint_def.get("value_ranges", {})
                }

        return {
            "goal": result["goal"],
            "instructions": result["instructions"],
            "stopping_criteria": result["stopping_criteria"],
            "tools_budgeting": result["tools_budgeting"],
            "dp_contract": dp_contract,
            "loop_iteration": 0,
            "should_continue": True,
            "evidence_quality_score": 0.0
        }

    except Exception as e:
        logger.error(f"Triage failed: {e}")
        raise

def node_controller(state: AgenticRunState) -> Dict[str, Any]:
    """
    Controller node - decides whether to continue or finalize.

    This node is called repeatedly, alternating with the ReAct agent subgraph.
    Budget hard-stops are enforced INSIDE tool wrappers. Here we do soft checks.

    Responsibilities:
    - Register budget in BudgetManager on first invocation
    - Synchronize usage from BudgetManager back to state
    - Check termination conditions (budget exhausted, finalize called, max iterations)
    - Decide whether to continue or move to synthesis

    Returns:
        Dict with: should_continue, termination_reason, budget_remaining (as dict), usage (as dict)
    """
    import json
    import uuid

    try:
        # Generate thread_id if not exists
        thread_id = state.get("_thread_id")
        if not thread_id:
            company_domain = state.get("company_context", {}).get("domain", "unknown")
            thread_id = f"{company_domain}_{uuid.uuid4().hex[:8]}"

        # Register budget in BudgetManager on first invocation
        if not BudgetManager.safe_get(thread_id):
            budgets = state.get("budgets", {})
            BudgetManager.set_budget(
                thread_id,
                Budget(
                    queries=budgets.get("max_queries", 3),
                    pages=budgets.get("max_pages", 6),
                    seconds=budgets.get("max_seconds", 60),
                    evidence_tokens=budgets.get("max_evidence_tokens", 3000),
                    ai_overviews=budgets.get("max_ai_overviews", 1),
                    pdf=budgets.get("max_pdf", 2),
                    google_ads=budgets.get("max_google_ads", 1)
                )
            )
            logger.info(f"Controller: Registered budget for thread {thread_id}")

        # Synchronize usage from BudgetManager back to state
        rec = BudgetManager.safe_get(thread_id)
        if rec:
            usage = {
                "queries": rec.usage.queries,
                "pages": rec.usage.pages,
                "seconds": rec.usage.seconds,
                "evidence_tokens": rec.usage.evidence_tokens,
                "ai_overviews": rec.usage.ai_overviews,
                "pdf": rec.usage.pdf,
                "google_ads": rec.usage.google_ads
            }
            budget_remaining = {
                "max_queries": rec.budget.queries - rec.usage.queries,
                "max_pages": rec.budget.pages - rec.usage.pages,
                "max_seconds": rec.budget.seconds - rec.usage.seconds,
                "max_evidence_tokens": rec.budget.evidence_tokens - rec.usage.evidence_tokens,
                "max_ai_overviews": rec.budget.ai_overviews - rec.usage.ai_overviews,
                "max_pdf": rec.budget.pdf - rec.usage.pdf,
                "max_google_ads": rec.budget.google_ads - rec.usage.google_ads
            }
        else:
            usage = state.get("usage", {})
            budget_remaining = state.get("budget_remaining", {})

        # Check for finalize action in messages
        finalize_called = False
        finalize_reasoning = None
        finalize_confidence = None

        messages = state.get("messages", [])
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if tool_call.get("name") == "finalize":
                        finalize_called = True
                        args = tool_call.get("args", {})
                        finalize_reasoning = args.get("reasoning", "")
                        finalize_confidence = args.get("confidence", 0.0)
                        logger.info(f"Controller: Agent called finalize (confidence: {finalize_confidence})")

        # Check termination conditions
        budget_exhausted = (
            budget_remaining.get("max_queries", 0) <= 0 or
            budget_remaining.get("max_pages", 0) <= 0 or
            budget_remaining.get("max_evidence_tokens", 0) <= 0 or
            budget_remaining.get("max_pdf", 0) <= 0
        )

        should_continue = True
        termination_reason = None

        if finalize_called:
            should_continue = False
            termination_reason = "agent_finalized"
        elif budget_exhausted:
            should_continue = False
            termination_reason = "budget_exhausted"
        elif state.get("loop_iteration", 0) >= 10:
            should_continue = False
            termination_reason = "max_iterations"

        # Build updates
        updates = {
            "_thread_id": thread_id,
            "usage": usage,
            "budget_remaining": budget_remaining,
            "should_continue": should_continue,
            "termination_reason": termination_reason
        }

        # If finalized, store reasoning and confidence
        if finalize_called and finalize_reasoning:
            updates["agent_thoughts"] = [finalize_reasoning]
            updates["evidence_quality_score"] = finalize_confidence or 0.0

        logger.info(f"Controller: continue={should_continue}, reason={termination_reason}, usage={usage}")
        return updates

    except Exception as e:
        logger.error(f"Controller failed: {e}", exc_info=True)
        return {
            "should_continue": False,
            "termination_reason": "error",
            "errors": [{"stage": "controller", "error": str(e)}]
        }

def node_final_synthesis(results, company_context: Dict[str, Any], competitor_context: Dict[str, Any], datapoint_definition: Dict[str, Any], goal: str, instructions: Any) -> Dict[str, Any]:
    """
    Terminal synthesis node that ALWAYS runs after ReAct loop stops.

    Uses llm.with_structured_output() to guarantee a structured SynthesisResponse
    regardless of how the loop ended (finalize, assistant stopped, max steps).

    Args:
        results: Results from ReAct agent with messages history
        company_context: YOUR company info (for reference)
        competitor_context: Competitor info (target of research)
        datapoint_definition: Datapoint definition
        goal: Research goal
        instructions: Research instructions

    Returns:
        Dict with: structured_response (SynthesisResponse), final_answer (str), final_confidence (float)
    """
    from .utils import pack_messages_for_synthesis
    from .graph import SynthesisResponse
    import os

    logger.info(f"Final synthesis starting - termination reason: {results.get('termination_reason', 'unknown')}")

    try:
        # Pack messages from history (with truncated markdowns) and get tools used
        packed_messages, tools_used = pack_messages_for_synthesis(results)
        # print("Packed messages for synthesis:")
        # print(packed_messages)  # DEBUG
        logger.info(f"Tools used during research: {tools_used}")

        # Format datapoint info
        import json
        
        # Format instructions
        instructions_str = ""
        if isinstance(instructions, list):
            instructions_str = "\n".join([f"{i+1}. {instr}" for i, instr in enumerate(instructions)])
        elif isinstance(instructions, str):
            instructions_str = instructions

        # Create synthesis template
        synthesis_template = """You are an expert competitive intelligence synthesis AI specialized in converting raw research data into actionable insights for sales and strategy teams.

Your job is to analyze all collected evidence about a COMPETITOR addressing a specific datapoint, and produce a final synthesis with strategic insights and recommended actions.

**YOUR COMPANY (for reference and comparison ONLY):**
{company_context}

**COMPETITOR (TARGET of research - what you analyzed):**
{competitor_context}

**CRITICAL UNDERSTANDING:**
- All findings must be ABOUT the competitor
- Use company_context ONLY for competitive comparison
- Research was conducted about the COMPETITOR, not YOUR company

**Research Goal:** {goal}

**Research Instructions:**
{instructions_str}

**Datapoint Definition:**
{datapoint_definition}

Review the conversation history below and create a structured synthesis following the exact schema.
If the finalize tool was called, use the exact reasoning and confidence provided there.
If no finalize was called, synthesize based on all evidence collected throughout the conversation.

**Company Verification Rules:**
- Only use information clearly tied to the target COMPETITOR
- Match by domain name, or company name + location/industry/size
- Ignore data from companies with similar names unless verified

**Output Format (respond with valid JSON only):**
{{{{
  "most_important_takeaway": "One punchy sentence headline that captures the most critical finding (max 15 words)",
  "answer": "4-6 sentence summary about the COMPETITOR with evidence",
  "insights": [
    "Short insight 1 about the competitor (one sentence)",
    "Short insight 2 about the competitor (one sentence)",
    "Short insight 3 about the competitor (one sentence)"
  ],
  "suggested_actions": [
    "Specific recommendation 1 for YOUR company based on competitor finding",
    "Specific recommendation 2 for YOUR company based on competitor finding"
  ],
  "concern_level": 1-5,
  "concern_rationale": "Why this datapoint should concern YOUR company at this level",
  "confidence": 0.0-1.0,
  "dp_value": "exact extracted value",
  "evidence_summary": {{{{
    "key_findings": ["finding 1", "finding 2"],
    "limitations": ["limitation 1"]
  }}}}
}}}}

**Field Requirements:**
- most_important_takeaway: Single punchy headline sentence (max 15 words) - this will be shown in notifications
- answer: 4-6 sentences summary about the COMPETITOR in non-technical language
- insights: 3-5 short, actionable insights about the COMPETITOR (one sentence each)
- suggested_actions: 2-4 specific recommendations for YOUR company based on what you learned
- concern_level: 1-5 scale (1=low concern, 5=critical threat/opportunity)
- concern_rationale: Brief explanation of why this matters to YOUR company
- confidence: number between 0.0-1.0 based on evidence strength
- dp_value: string with exact extracted value
- evidence_summary.key_findings: array of strings
- evidence_summary.limitations: array of strings

Compacted conversation history:

{packed_messages}

Now produce the final synthesis as valid JSON adhering to the format and requirements above.
"""

        # Use OpenRouterAdapter for synthesis
        from api_clients.open_router import OpenRouterAdapter

        # Format synthesis prompt
        prompt = synthesis_template.format(
            company_context=json.dumps(company_context, indent=2),
            competitor_context=json.dumps(competitor_context, indent=2),
            goal=goal,
            instructions_str=instructions_str,
            datapoint_definition=str(datapoint_definition),
            packed_messages=packed_messages
        )

        adapter = OpenRouterAdapter()
        response_text = adapter.get_completion(
            prompt=prompt,
            model="google/gemini-2.5-flash",
            temperature=0,
            max_output_tokens=4000
        )

        # Parse JSON response
        synthesis_dict = json.loads(response_text.strip().replace("```json", "").replace("```", ""))

        logger.info(f"Final synthesis completed - answer: {synthesis_dict.get('answer', 'N/A')}, confidence: {synthesis_dict.get('confidence', 0.0)}")
        # Add tools_used metadata to synthesis_dict
        synthesis_dict['tools_used'] = list(tools_used)
        # Return state update with structured_response
        return synthesis_dict

    except Exception as e:
        logger.error(f"Final synthesis failed: {e}")

        # Return a valid synthesis dict structure on error
        return {
            "answer": f"Synthesis failed: {str(e)}",
            "confidence": 0.0,
            "mapping_rationale": "",
            "dp_value": "",
            "mapped_range": "",
            "evidence_summary": {
                "key_findings": [],
                "limitations": [f"Synthesis error: {str(e)}"]
            }
        }
