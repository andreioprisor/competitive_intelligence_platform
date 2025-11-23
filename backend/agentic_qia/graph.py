"""
LangGraph orchestration for agentic QIA with built-in ReAct agent
"""
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from .state import AgenticRunState
from .nodes import node_triage, node_controller, node_final_synthesis
from .tools import create_budget_aware_tools, format_tools_for_llm
from typing import Dict, Any, Callable, Optional, Type, List
from pydantic import BaseModel, Field
from httpx import AsyncClient, Limits
import logging
import os
import json
import dataclasses
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

@dataclasses.dataclass
class ContextSchema:
    company_name: str
    company_domain: str
    company_industry: str
    company_size: str
    datapoint_definition: Dict[str, Any]
    datapoint_name: str
    datapoint_value_ranges: Dict[str, str]


# Pydantic models for synthesis response schema
class EvidenceSummary(BaseModel):
    """Summary of evidence quality"""
    key_findings: List[str] = Field(description="Primary findings from research")
    limitations: List[str] = Field(description="Gaps or uncertainties in evidence")


class SynthesisResponse(BaseModel):
    """Final structured response from synthesis - enhanced for competitive intelligence"""
    answer: str = Field(description="4-6 sentence detailed reasoning about the competitor with evidence")
    insights: List[str] = Field(description="3-5 short, actionable insights about the competitor (one sentence each)")
    suggested_actions: List[str] = Field(description="2-4 specific recommendations for YOUR company based on this competitor insight")
    concern_level: int = Field(ge=1, le=5, description="How much this datapoint should concern your company (1=low, 5=critical)")
    concern_rationale: str = Field(description="Brief explanation of why this concern level was assigned")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    dp_value: str = Field(default="", description="Extracted datapoint value")
    evidence_summary: EvidenceSummary = Field(description="Summary of key findings and limitations")

class ReactGraph:
    """
    Encapsulates the agentic QIA workflow using LangGraph's built-in ReAct agent.

    Handles:
    - Planning step (triage) to generate research plan
    - ReAct agent with pre/post hooks for message management and guardrails
    - Company and datapoint context injection
    - Budget tracking and enforcement
    """

    def __init__(self, company_context: Dict[str, Any], competitor_context: Dict[str, Any], datapoint_context: Dict[str, Any], prospect: Optional[Any] = None):
        """
        Initialize ReactGraph with company, competitor and datapoint context.

        Args:
            company_context: Dict with YOUR company info (for reference)
            competitor_context: Dict with competitor info (target of research)
            datapoint_context: Dict with keys: dp_name, description/definition
            prospect: Optional Prospect object with enriched data (for accessing LinkedIn posts, etc.)
        """
        self.company_context = company_context
        self.competitor_context = competitor_context
        self.datapoint_context = datapoint_context
        self.prospect = prospect
        self.prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        self.react_prompt_path = os.path.join(self.prompts_dir, "react_system.md")

        # Initialize budget tracking
        self.budget_remaining = {}

        # Initialize rate limiter for TPM enforcement
        from .rate_limiter import create_gemini_rate_limiter
        # Disable rate limiter for testing
        self.rate_limiter = None

        # Initialize model and tools
        # self.llm = ChatGoogleGenerativeAI(
        #     model="gemini-flash-latest",
        #     google_api_key=os.getenv('GEMINI_API_KEY'),
        #     temperature=0,
        #     max_output_tokens=2000,
        # )
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        self.llm = ChatOpenAI(
            model="openai/gpt-5.1",
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            max_tokens=3000,
            http_async_client=AsyncClient(
                limits=Limits(max_keepalive_connections=0)
            )
        )

        # self.llm = ChatXAI(
        #     model="grok-4-fast",
        #     temperature=0.1,
        #     xai_api_key=os.getenv('XAI_API_KEY'),
        #     max_tokens=None,
        #     timeout=None,
        #     max_retries=2,
        # )

        # Create tools with prospect bound via closure (if prospect provided)
        self.tools = create_budget_aware_tools(prospect=self.prospect)

        # Build agent once during initialization
        self.agent = self.build_agent()
        if not self.rate_limiter:
            logger.warning("Rate limiter is disabled for ReactGraph - no TPM enforcement!")

        logger.info(f"ReactGraph initialized for {company_context.get('domain', 'unknown')}", extra={
            "company_domain": company_context.get("domain", "unknown"),
            "datapoint_name": datapoint_context.get("dp_name", "unknown"),
            "rate_limiter": "enabled" if self.rate_limiter else "disabled",
            "rate_limiter_tpm": f"{self.rate_limiter.limit:,} TPM" if self.rate_limiter else "N/A"
        })

    def create_state_schema(self) -> Type:
        """
        Returns the state schema for the ReAct agent.

        Uses existing AgenticRunState which includes required keys:
        - messages: List[BaseMessage]
        - remaining_steps: int
        """
        return AgenticRunState

    def initialize_state(self, prompt: str, plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create initial state for the ReAct agent.

        Args:
            prompt: User's research question
            plan: Optional plan dict from planning step

        Returns:
            State dict with messages, remaining_steps, and all other fields
        """
        state = {
            "prompt": prompt,
            "company_context": self.company_context,
            "competitor_context": self.competitor_context,
            "datapoint_definition": self.datapoint_context,
            "tools_registry": format_tools_for_llm(),

            # Required by ReAct agent
            "messages": [HumanMessage(content=prompt)],
            "remaining_steps": 50,  # Max iterations for ReAct loop

            # Planning fields (populated if plan provided)
            "goal": plan.get("goal", "") if plan else "",
            "instructions": plan.get("instructions", "") if plan else "",
            "stopping_criteria": plan.get("stopping_criteria", "") if plan else "",
            "obtainability": plan.get("obtainability", "") if plan else "",
            "budgets": plan.get("budgets", {}) if plan else {},
            "budget_remaining": plan.get("budget_remaining", {}) if plan else {},
            "dp_contract": plan.get("dp_contract") if plan else None,

            # Budget tracking
            "_thread_id": None,
            "loop_iteration": 0,
            "usage": {},

            # Evidence collection
            "tool_calls": [],
            "evidence_collected": [],
            "candidates": [],
            "discovered_urls": [],
            "ai_overview_content": [],

            # Agent decision state
            "agent_thoughts": [],
            "evidence_quality_score": 0.0,
            "should_continue": True,
            "termination_reason": None,

            # Internal routing
            "_next_tool": None,
            "_tool_args": None,

            # Final outputs
            "final_answer": None,
            "final_confidence": None,
            "final_json": None,
            "structured_response": None,  # Generated by terminal synthesis node

            # Telemetry
            "telemetry": [],
            "errors": []
        }

        logger.info(f"State initialized with remaining_steps={state['remaining_steps']}")
        return state

    def run_planning_step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run planning/triage step to generate research plan.

        Calls existing node_triage() to generate:
        - goal: What specific information to find
        - instructions: High-level plan for retrieval
        - stopping_criteria: When to consider search complete
        - obtainability: Difficulty level
        - budgets: Resource allocation

        Args:
            state: Current state dict

        Returns:
            Plan dict with goal, instructions, stopping_criteria, budgets, etc.
        """
        logger.info("Running planning step (triage)")
        plan_update = node_triage(state)
        logger.info(f"Planning complete: obtainability={plan_update.get('obtainability')}, " +
                   f"budgets={plan_update.get('budgets')}")
        return plan_update

    def _load_synthesis_prompt(self) -> str:
        """
        Load and format synthesis prompt for response_format.

        Returns concise synthesis instructions for structured output generation.
        """
        # Load the full synthesis template
        synthesis_prompt_path = os.path.join(self.prompts_dir, "final_synthesis.md")
        with open(synthesis_prompt_path, "r") as f:
            full_template = f.read()

        # Create a concise prompt that references state fields
        # The actual values will be populated from the graph state automatically
        synthesis_instructions = """# Synthesis Instructions

You have completed research and gathered evidence. Now synthesize your findings into a structured response.

**Your Task:**
1. Review all evidence from tool results (SERP results, crawled pages, AI overviews)
2. Filter out irrelevant content (navigation, ads, boilerplate)
3. Extract key information that answers the original research question
4. Map findings to datapoint value ranges if applicable
5. Provide citations from crawled URLs
6. Assess confidence based on evidence quality

**Company Verification Rules:**
- Only use information clearly tied to the target company
- Match by domain name, or company name + location/industry/size
- Ignore data from companies with similar names unless verified

**Output Requirements:**
- Answer: 4-6 sentences addressing the datapoint with inline citations like [Source Name]
- Confidence: 0.0-1.0 based on evidence strength
- Mapping Rationale: Explain why you selected the mapped range
- Datapoint Value: Exact extracted value if available
- Mapped Range: Selected range from datapoint definition
- Evidence Summary: Key findings and limitations
- Respect the output schema

Be concise, factual, and transparent about evidence quality."""

        return synthesis_instructions

    def create_llm_prehook(self) -> Callable:
        """
        Create pre-model hook that runs before each LLM call in ReAct loop.

        Used for message history management (trimming, summarization).

        Returns:
            Callable with signature (state) -> state_update
        """
        async def prehook(state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Trim message history if it exceeds threshold.
            Also enforce rate limiting by reserving tokens before LLM call.

            Strategy: Keep system messages + last 19 conversation messages = max 20 total
            """
            import time
            logging.info("Pre-hook: Checking message history for trimming")
            messages = state.get("messages", [])

            # If more than 25 messages, trim to last 20
            if len(messages) > 25:
                logger.info(f"Trimming messages from {len(messages)} to 20")

                # Preserve system messages and keep last 19 non-system messages
                system_messages = [m for m in messages if hasattr(m, 'type') and m.type == "system"][:1]
                non_system_messages = [m for m in messages if not (hasattr(m, 'type') and m.type == "system")][-19:]

                # Clear history by only returning trimmed messages (don't use RemoveMessage with agent.invoke)
                # RemoveMessage objects cause "Got unknown type" errors when passed through agent
                return {
                    "messages": [
                        *system_messages,
                        *non_system_messages
                    ]
                }

            logger.info(f"Messages count {len(messages)} within limit, no trimming needed")

            # Rate limiting: Reserve tokens for upcoming LLM call
            if self.rate_limiter:
                try:
                    # Convert messages to BaseMessage objects if needed for token counting
                    converted_messages = []
                    for msg in messages:
                        # Already a BaseMessage
                        if hasattr(msg, 'type'):
                            converted_messages.append(msg)
                        # Dict format - convert based on type
                        elif isinstance(msg, dict):
                            msg_type = msg.get('type', 'human')
                            content = msg.get('content', '')

                            if msg_type == 'remove':
                                continue  # Skip RemoveMessage in token counting

                            if msg_type == 'human':
                                converted_messages.append(HumanMessage(content=content))
                            elif msg_type in ['ai', 'assistant']:
                                converted_messages.append(AIMessage(content=content))
                            elif msg_type == 'system':
                                converted_messages.append(SystemMessage(content=content))
                            elif msg_type == 'tool':
                                converted_messages.append(ToolMessage(content=content, tool_call_id=msg.get('tool_call_id', '')))
                            else:
                                # Default to HumanMessage
                                converted_messages.append(HumanMessage(content=str(msg)))
                        else:
                            # Fallback for other formats
                            converted_messages.append(HumanMessage(content=str(msg)))

                    # Use LLM's built-in token counting for accurate count
                    input_tokens = self.llm.get_num_tokens_from_messages(converted_messages)

                    logger.info(f"Pre-hook: Counted {input_tokens:,} input tokens, calling rate limiter")

                    # Track timing around rate limiter call
                    rate_limiter_start = time.time()

                    # Reserve tokens (async, can be interrupted by timeouts)
                    success = await self.rate_limiter.reserve_tokens(
                        token_count=input_tokens,
                        max_wait=30.0  # Wait up to 30 seconds (reduced from 120s)
                    )

                    rate_limiter_duration = time.time() - rate_limiter_start
                    logger.info(f"Pre-hook: Rate limiter completed in {rate_limiter_duration:.2f}s (success={success})")

                    if not success:
                        logger.error(f"Pre-hook: Rate limiter timeout after {rate_limiter_duration:.1f}s - proceeding anyway")
                except Exception as e:
                    logger.error(f"Pre-hook: Rate limiter error: {e} - proceeding anyway", exc_info=True)

            # No trimming needed
            return {}

        return prehook

    def create_llm_posthook(self) -> Callable:
        """
        Create post-model hook that runs after each LLM call in ReAct loop.

        Detects termination conditions and sets routing signals:
        - finalize tool called → should_continue=False
        - AI message with no tool calls → should_continue=False
        - Max steps reached → should_continue=False

        Also tracks tool usage and injects budget reminder messages.

        Returns:
            Callable with signature (state) -> state_update
        """
        def posthook(state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Detect termination conditions, track budget, and inject budget messages.
            """
            messages = state.get("messages", [])
            if not messages:
                return {}

            last_message = messages[-1]
            # logging.info("Remaining steps after LLM call:", extra={"remaining_steps": remaining_steps})

            # Check if last message has tool calls (handle multiple formats)
            tool_calls = getattr(last_message, "tool_calls", None) or \
                        getattr(last_message, "additional_kwargs", {}).get("tool_calls")

            # Check message type - is it an AI message?
            message_type = getattr(last_message, "type", None) or last_message.get("type")
            is_ai_message = message_type in ["ai", "assistant"]

            # Track tool usage and decrement budget
            if tool_calls:
                tool_names = [tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown')
                             for tc in tool_calls]
                logger.info(f"Post-hook: Agent called {len(tool_calls)} tool(s): {tool_names}")

                # Decrement budget based on actual usage (parameters, not just tool calls)
                for tc in tool_calls:
                    tool_name = tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown')

                    # Extract args to count actual usage
                    args = tc.get('args') if isinstance(tc, dict) else getattr(tc, 'args', {})

                    # Calculate actual usage based on tool type
                    if tool_name == 'serp':
                        # serp budget is per query, not per tool call
                        queries = args.get('queries', []) if isinstance(args, dict) else []
                        usage_count = len(queries) if queries else 1
                    elif tool_name == 'crawl':
                        # crawl budget is per URL, not per tool call
                        urls = args.get('urls', []) if isinstance(args, dict) else []
                        usage_count = len(urls) if urls else 1
                    else:
                        # Other tools count as 1 per call
                        usage_count = 1

                    # Decrement budget (clamp at 0)
                    if tool_name in self.budget_remaining:
                        self.budget_remaining[tool_name] = max(0, self.budget_remaining[tool_name] - usage_count)
                        logger.info(f"Post-hook: Decremented {tool_name} budget by {usage_count} to {self.budget_remaining[tool_name]}")

                # Check if finalize was called
                if "finalize" in tool_names:
                    logger.info("Post-hook: Finalize tool called - stopping research loop")
                    return {
                        "should_continue": False,
                        "termination_reason": "finalize_requested",
                        "budget_remaining": self.budget_remaining.copy()
                    }

            # Format budget message
            # budget_parts = [f"{count} {tool}" for tool, count in self.budget_remaining.items()]
            budget_parts = []
            for tool, count in self.budget_remaining.items():
                if tool == "urls":
                    budget_parts.append(f"{count} URLs to crawl")
                elif tool == "serp":
                    budget_parts.append(f"{count} SERP queries")
                else:
                    budget_parts.append(f"{count} {tool} tool calls")
            budget_str = f"Budget Remaining: {', '.join(budget_parts)}"
            logger.info(f"Post-hook: {budget_str}")

            # Inject budget message into conversation
            from langchain_core.messages import HumanMessage
            budget_message = HumanMessage(content=f"[System] {budget_str}")

            # Continue the loop with budget message
            return {
                "budget_remaining": self.budget_remaining.copy(),
                "messages": [budget_message]
            }

        return posthook

    def create_react_prompt(self, plan: Dict[str, Any]) -> str:
        """
        Load and format the ReAct agent prompt from react_agent.md template.

        Args:
            plan: Plan dict from triage with goal, instructions, stopping_criteria, etc.

        Returns:
            Formatted prompt string for ReAct agent
        """
        from datetime import datetime

        react_agent_prompt_path = os.path.join(self.prompts_dir, "react_agent.md")

        with open(react_agent_prompt_path, "r") as f:
            prompt_template = f.read()

        # Format instructions - convert list to numbered string
        instructions_raw = plan.get("instructions", [])
        if isinstance(instructions_raw, list):
            instructions_str = "\n".join([f"{i+1}. {instr}" for i, instr in enumerate(instructions_raw)])
        else:
            instructions_str = str(instructions_raw)

        # Format company context
        company_context_str = f"""
- Industry: {self.company_context.get('industry', 'N/A')}
- Size: {self.company_context.get('size', 'N/A')}
- Location: {self.company_context.get('location', 'N/A')}
- Description: {self.company_context.get('description', 'N/A')}
        """.strip()

        # Get current date for time-aware agent execution
        current_datetime = datetime.now().date().isoformat()

        tools_budget_dict = plan.get("tools_budgeting", {})
        tools_budget_str = ", ".join([f"{v} {k} tool calls" for k, v in tools_budget_dict.items()])

        prompt = prompt_template.replace("{{goal}}", plan.get("goal", "")) \
                                .replace("{{instructions}}", instructions_str) \
                                .replace("{{stopping_criteria}}", plan.get("stopping_criteria", "")) \
                                .replace("{{dp_name}}", self.datapoint_context.get("dp_name", "")) \
                                .replace("{{company_domain}}", self.company_context.get("domain", "")) \
                                .replace("{{company_name}}", self.company_context.get("name", "")) \
                                .replace("{{company_context}}", company_context_str) \
                                .replace("{{current_datetime}}", current_datetime) \
                                .replace("{{definition}}", self.datapoint_context.get("description", "")) \
                                .replace("{{value_ranges}}", json.dumps(self.datapoint_context.get("value_ranges", {}), indent=2)) \
                                .replace("{{tools_budgeting}}", tools_budget_str) \
                                .replace("{{max_serp}}", str(plan.get("tools_budgeting", {}).get("serp", 5))) \
                                .replace("{{max_crawl}}", str(plan.get("tools_budgeting", {}).get("crawl", 10))) \
                                .replace("{{max_ai_overview}}", str(plan.get("tools_budgeting", {}).get("ai_overview", 2))) \

        return prompt

    def build_agent(self) -> Any:
        """
        Build the ReAct agent with all configurations.

        Returns:
            Compiled LangGraph agent
        """

        # Load synthesis prompt for response_format
        synthesis_prompt = self._load_synthesis_prompt()
        # state = self.initialize_state("Initial prompt for agent build")

        # # Step 2: Run planning step to generate plan
        # plan = self.run_planning_step(state)

        # # Step 3: Create formatted prompt using plan
        # formatted_prompt = self.create_react_prompt(plan)
        # print(formatted_prompt)

        # Create ReAct agent with response_format for structured synthesis
        # Note: Don't bind_tools to model manually - let create_react_agent handle it
        agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            # prompt=formatted_prompt,
            pre_model_hook=self.create_llm_prehook(),
            post_model_hook=self.create_llm_posthook(),
            state_schema=self.create_state_schema(),
            context_schema=ContextSchema,
            version="v2"
        )

        logger.info("ReAct agent built successfully with structured synthesis response")
        return agent

    def invoke(self, prompt: str =None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the full agentic QIA pipeline.

        Flow:
        1. Initialize state with user message
        2. Run planning step to generate plan
        3. Invoke agent with state dict (plan fields will be used by dynamic system prompt)
        4. Return final state

        Args:
            prompt: User's research question
            config: Optional config for LangGraph invocation

        Returns:
            Final state dict with results
        """
        logger.info(f"ReactGraph.invoke() called with prompt: {prompt}")
        # from leadora.adapters.agentic_adapters.llm_adapter import LLMAdapter
        
        # Step 1: Initialize state with user message
        state = self.initialize_state(prompt)

        # Step 2: Run planning step to generate plan
        plan = self.run_planning_step(state)
        state["goal"] = plan.get("goal", "")
        state["instructions"] = plan.get("instructions", "")
        state["stopping_criteria"] = plan.get("stopping_criteria", "")
        state["tools_budgeting"] = plan.get("tools_budgeting", {})

        # Initialize budget tracking from triage
        self.budget_remaining = plan.get("tools_budgeting", {}).copy()
        state["budget_remaining"] = self.budget_remaining.copy()

        # Step 3: Create formatted prompt using plan
        formatted_prompt = self.create_react_prompt(plan)
        # print(formatted_prompt)

        # Step 4: Generate thread_id for budget tracking

        logging.info("Generated plan for ReAct agent:")
        logging.info(json.dumps(plan, indent=2))

        # Step 5: Invoke agent with formatted prompt
        logger.info("Invoking ReAct agent with formatted prompt")

        # Configure recursion limit
        if config is None:
            config = {}
        config["recursion_limit"] = 100  # Increase from default 25 to 100

        raw_result = self.agent.invoke(
            {
                "messages": [
                    {
                        "type": "human",
                        "content": formatted_prompt
                    }
                ],
            },
            config=config
        )
        logger.info("ReAct agent completed - running terminal synthesis")

        # Step 6: Run terminal synthesis to generate structured response
        # This ALWAYS runs regardless of how the ReAct loop ended
        
        synthesis_result = node_final_synthesis(
            results=raw_result,
            company_context=self.company_context,
            competitor_context=self.competitor_context,
            datapoint_definition=self.datapoint_context,
            goal=state["goal"],
            instructions=state["instructions"],
        )

        # Check if search_linkedin_posts_tool was used and add LinkedIn URL to citations
        tools_used = synthesis_result.get('tools_used', [])
        logger.info(f"Tools used in synthesis: {tools_used}")
        if self.prospect and 'search_linkedin_posts_tool' in tools_used:
            linkedin_simple = getattr(self.prospect, 'linkedin_simple_data', None)
            linkedin_url = getattr(linkedin_simple, 'linkedin_url', None) if linkedin_simple else None
            if linkedin_url:
                logger.info(f"search_linkedin_posts_tool was used, adding LinkedIn URL to citations: {linkedin_url}")
                if "citations" not in synthesis_result:
                    synthesis_result["citations"] = []
                if linkedin_url not in synthesis_result["citations"]:
                    synthesis_result["citations"].append(linkedin_url)

        raw_result["structured_response"] = synthesis_result

        logger.info(f"Pipeline complete - termination: {synthesis_result}")
        # print("Final result:")
        # print(raw_result)
        # print(json.dumps(raw_result, indent=2))
        return raw_result

    async def ainvoke(self, prompt: str = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Async version of invoke() - required when using async pre/post hooks.

        Run the full agentic QIA pipeline asynchronously.

        Flow:
        1. Initialize state with user message
        2. Run planning step to generate plan
        3. Invoke agent with state dict (plan fields will be used by dynamic system prompt)
        4. Return final state

        Args:
            prompt: User's research question
            config: Optional config for LangGraph invocation

        Returns:
            Final state dict with results
        """
        logger.info(f"ReactGraph.ainvoke() called with prompt: {prompt}")

        # Step 1: Initialize state with user message
        state = self.initialize_state(prompt)

        # Step 2: Run planning step to generate plan
        plan = self.run_planning_step(state)
        state["goal"] = plan.get("goal", "")
        state["instructions"] = plan.get("instructions", "")
        state["stopping_criteria"] = plan.get("stopping_criteria", "")
        state["tools_budgeting"] = plan.get("tools_budgeting", {})

        # Initialize budget tracking from triage
        self.budget_remaining = plan.get("tools_budgeting", {}).copy()
        state["budget_remaining"] = self.budget_remaining.copy()

        # Step 3: Create formatted prompt using plan
        formatted_prompt = self.create_react_prompt(plan)

        # Step 4: Generate thread_id for budget tracking
        logging.info("Generated plan for ReAct agent:")
        logging.info(json.dumps(plan, indent=2))

        # Step 5: Invoke agent with formatted prompt (async)
        logger.info("Invoking ReAct agent with formatted prompt (async)")

        # Configure recursion limit
        if config is None:
            config = {}
        config["recursion_limit"] = 100  # Increase from default 25 to 100

        raw_result = await self.agent.ainvoke(
            {
                "messages": [
                    {
                        "type": "human",
                        "content": formatted_prompt
                    }
                ],
            },
            config=config
        )
        logger.info("ReAct agent completed - running terminal synthesis")

        # Step 6: Run terminal synthesis to generate structured response
        # This ALWAYS runs regardless of how the ReAct loop ended

        synthesis_result = node_final_synthesis(
            results=raw_result,
            company_context=self.company_context,
            competitor_context=self.competitor_context,
            datapoint_definition=self.datapoint_context,
            goal=state["goal"],
            instructions=state["instructions"],
        )

        # Check if search_linkedin_posts_tool was used and add LinkedIn URL to citations
        tools_used = synthesis_result.get('tools_used', [])
        logger.info(f"Tools used in synthesis: {tools_used}")
        if self.prospect and 'search_linkedin_posts_tool' in tools_used:
            linkedin_simple = getattr(self.prospect, 'linkedin_simple_data', None)
            linkedin_url = getattr(linkedin_simple, 'linkedin_url', None) if linkedin_simple else None
            if linkedin_url:
                logger.info(f"search_linkedin_posts_tool was used, adding LinkedIn URL to citations: {linkedin_url}")
                if "citations" not in synthesis_result:
                    synthesis_result["citations"] = []
                if linkedin_url not in synthesis_result["citations"]:
                    synthesis_result["citations"].append(linkedin_url)

        raw_result["structured_response"] = synthesis_result

        logger.info(f"Pipeline complete - termination: {synthesis_result}")

        # Cleanup: Close async client to prevent resource warnings
        try:
            if hasattr(self.llm, 'async_client') and self.llm.async_client:
                await self.llm.async_client.aclose()
        except Exception as e:
            logger.warning(f"Failed to close LLM async client: {e}")

        return raw_result

    @staticmethod
    def serialize_response(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize LangGraph response to clean JSON format suitable for API responses.

        Extracts only the synthesis results while logging the full details.

        Args:
            result: Raw result dict from agent.invoke() containing messages, structured_response, etc.

        Returns:
            Clean JSON dict with only synthesis data:
            {
                "answer": str,
                "confidence": float,
                "citations": List[str],
                "dp_fields": {
                    "mapping_rationale": str,
                    "dp_name": str,
                    "mapped_range": str,
                    "dp_value": str
                },
                "evidence_summary": {
                    "key_findings": List[str],
                    "limitations": List[str]
                }
            }
        """
        logger.info("Serializing ReactGraph response - extracting synthesis results")
        print("Result before db serialization:")
        print(result)
        # Extract structured_response (SynthesisResponse)
        structured_response = result.get('structured_response')
        metrics = result.get('metrics', {})
        urls_crawled = metrics.get('urls_crawled', [])
        queries_made = metrics.get('queries_executed', [])

        if not structured_response:
            logger.warning("No structured_response found in result")
            answer = result.get('final_answer', 'No answer generated')
            return {
                "answer": answer,
                "confidence": 0.0,
                "mapping_rationale": "",
                "dp_value": "",
                "mapped_range": "",
                "evidence_summary": {
                    "key_findings": [],
                    "limitations": []
                },
                "citations": urls_crawled
            }
        
        structured_response['citations'] = urls_crawled
        structured_response['queries_made'] = queries_made

        # Convert Pydantic model to dict
        if hasattr(structured_response, 'model_dump'):
            synthesis_dict = structured_response.model_dump()
        elif hasattr(structured_response, 'dict'):
            synthesis_dict = structured_response.dict()
        else:
            synthesis_dict = structured_response

        logger.info(f"Synthesis extracted - Confidence: {synthesis_dict.get('confidence', 0):.2%}")
        logger.info(f"Mapped range: {synthesis_dict.get('mapped_range', 'unknown')}")

        # Return only synthesis results (already flattened in new model)
        return synthesis_dict

    @staticmethod
    def parse_result_messages(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the final result messages into a structured format with tool calls and results.

        This uses the utils.parse_logged_chunk to normalize messages into a consistent format
        that extracts tool calls, tool results, and final AI messages.

        Args:
            result: Raw result dict from agent.invoke() containing messages

        Returns:
            Parsed dict with:
            - messages: ordered list of {role, content, tool_call?, tool_result?}
            - tool_calls: list of {name, args, id?}
            - tool_results: list of {name?, result, tool_call_id?}
            - final_ai_message: last assistant text
        """
        from .utils import parse_logged_chunk

        # Create a chunk-like structure from the result
        chunk = {
            "type": "final_result",
            "payload": {
                "input": {
                    "messages": result.get("messages", [])
                }
            }
        }

        parsed = parse_logged_chunk(chunk)
        logger.info(f"Parsed {len(parsed['messages'])} messages, {len(parsed['tool_calls'])} tool calls, {len(parsed['tool_results'])} tool results")
        if "structured_response" in result:
            parsed["structured_response"] = result["structured_response"]

        return parsed

# Example usage
if __name__ == "__main__":
    # agent = build_agentic_app()
    import asyncio
    # from langgraph.prebuilt import create_react_agent

    # setup logging
    logging.basicConfig(level=logging.INFO)
    # from pythonjsonlogger import jsonlogger
    company_context = {
        "name": "VWO",
        "domain": "vwo.com",
        "industry": "SaaS / Conversion Rate Optimization",
        "size": "200-500 employees"
    }

    # Create ReactGraph with company and datapoint context
    competitor_context = {
        "name": "Omniconvert",
        "domain": "omniconvert.com",
        "industry": "SaaS / Conversion Rate Optimization",
        "size": "50-100 employees"
    }

    datapoint_context = {
        "dp_name": "Current Google Ads Strategy Analysis",
        "definition": "Analyze Omniconvert's current Google Ads advertising strategy including ad creatives, messaging, targeting keywords, value propositions, and campaign patterns from the last 30 days.",
        "value_ranges": {
            "bad": "No ads found or only 1-2 ads with minimal information",
            "average": "Found ads but missing detailed analysis of messaging patterns or targeting strategy",
            "good": "Multiple ads analyzed with clear messaging themes, keywords, and value propositions identified",
            "best": "Comprehensive analysis including ad variations, messaging evolution, targeting keywords, CTAs, unique value propositions, and strategic insights across different ad formats"
        }
    }

    async def main():
        graph = ReactGraph(company_context, datapoint_context)
        result = await graph.ainvoke(
            prompt="Find what cloud technologies is emag.ro using."
        )
        return result

    result = asyncio.run(main())


    # agent = build_agentic_app()
    # result = agent.invoke({
    #     "messages": [
    #         {
    #             "type": "human",
    #             "content": "Find what cloud technologies is emag.ro using. Use the serp tool to find job pages by searching for things like 'emag.ro cloud engineer job', 'emag.ro devops job'. After you have the results, pick urls most relevant to engineering jobs within emag, by snippets and url strings and use the crawl tool to crawl those job pages and look for mentions of cloud technologies. Try to look at multiple jobs, not just one. Summarize your findings in a final answer."
    #         }
    #     ],
    #     "company_context": company_context,
    #     "datapoint_definition": datapoint_context,
    #     "remaining_steps": 10,
    #     "_thread_id": "test-thread-001"
    # })


    # from .tools import crawl_tool
    # import asyncio

    # # res = await crawl_tool(["https://jobs-cee.pwc.com/ce/en/job/671943WD/Azure-PaaS-Engineer-24x7-Cloud-Operations-Team-Manager"])

    # res = asyncio.run(crawl_tool(["https://jobs-cee.pwc.com/ro/ro/job/631894WD/Senior-Azure-Cloud-Engineer"]))
    # with open("crawl_result.html", "w") as f:
    #     json.dump(res[0].get("html"), f, indent=2)

    # with open("markdown_result.md", "w") as f:
    #     json.dump(res[0].get("markdown"), f, indent=2)
