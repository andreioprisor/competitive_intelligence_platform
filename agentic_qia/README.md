# Agentic QIA - ReAct-Style Research Agent

True agentic implementation of QIA using LangGraph with tool-based loop execution.

## Architecture

```
START → Triage → [AGENT LOOP] → Synthesis → END

[AGENT LOOP]:
  Reasoning → Tool Execution → Loop Control
      ↑______________|
         (loops until termination)
```

## Files

### Core Components

- **[state.py](state.py)** - Enhanced state schema with loop tracking
  - `AgenticRunState`: TypedDict with loop iteration, budget tracking, tool call history
  - Annotated fields for state accumulation (evidence, tool_calls, agent_thoughts)

- **[graph.py](graph.py)** - LangGraph orchestration
  - `build_agentic_app()`: Builds graph with conditional routing
  - `should_continue_loop()`: Routing function for loop control
  - Edges: triage → reasoning → tool_execution → loop_control → (reasoning | synthesis)

- **[nodes.py](nodes.py)** - Node implementation interfaces
  - `node_triage`: Convert prompt to research plan
  - `node_agent_reasoning`: ReAct decision loop
  - `node_tool_execution`: Execute selected tool
  - `node_loop_controller`: Check termination conditions
  - `node_final_synthesis`: Create final answer

- **[tools.py](tools.py)** - Tool templates
  - `serp_tool`: Web search with reranking
  - `crawl_tool`: Extract webpage content
  - `discover_urls_tool`: Find company website pages (NEW)
  - `ai_overview_tool`: Get Google AI Overview
  - `get_tool_cost()`: Budget calculation utility

### Prompts

- **[prompts/agent_reasoning.md](prompts/agent_reasoning.md)** - ReAct reasoning template
  - Tool descriptions with cost/purpose/usage
  - Decision framework and termination criteria
  - JSON output schema
  - Examples for each scenario

## Key Differences from `qia_agent`

| Feature | `qia_agent` (Linear) | `agentic_qia` (Loop) |
|---------|---------------------|----------------------|
| **Execution** | Fixed pipeline | Dynamic tool selection |
| **Queries** | All generated upfront | Generated on-demand |
| **Termination** | Always runs full pipeline | Early stop when sufficient |
| **Budget** | Set once, no monitoring | Real-time tracking |
| **Reasoning** | None | ReAct thought chain |
| **Tools** | Hard-coded in nodes | Registry-based, extensible |

## Usage

```python
from leadora.adapters.agentic_qia import build_agentic_app, create_initial_state

# Build graph
app = build_agentic_app()

# Create initial state
state = create_initial_state(
    prompt="What is TechCorp's employee count?",
    company_context={
        "name": "TechCorp",
        "domain": "techcorp.com",
        "industry": "Technology"
    }
)

# Run agent
result = app.invoke(state)

# Access results
print(result["final_answer"])
print(f"Confidence: {result['final_confidence']}")
print(f"Iterations: {result['loop_iteration']}")
print(f"Termination: {result['termination_reason']}")
```

## Implementation Status

### Phase 1: Structure ✅ COMPLETE
- [x] State schema with loop tracking
- [x] Graph with conditional routing
- [x] Node interfaces (documentation only)
- [x] Tool templates (documentation only)
- [x] ReAct reasoning prompt

### Phase 2: Implementation (TODO)
- [ ] Implement tool functions (serp, crawl, discover_urls, ai_overview)
- [ ] Implement LLM-based agent reasoning node
- [ ] Implement triage node (reuse from qia_agent)
- [ ] Implement synthesis node (reuse from qia_agent)
- [ ] Implement tool execution with budget tracking
- [ ] Add budget_tracker utility
- [ ] Add quality_assessor utility

### Phase 3: Testing (TODO)
- [ ] Unit tests for each node
- [ ] Integration test for full graph
- [ ] Test budget exhaustion scenarios
- [ ] Test early termination with high confidence
- [ ] Test loop iteration limits
- [ ] Compare metrics vs qia_agent

### Phase 4: Optimization (TODO)
- [ ] Tune ReAct prompt based on failure cases
- [ ] Optimize tool selection heuristics
- [ ] Add caching for repeated queries
- [ ] Implement parallel tool execution where possible

## Design Principles

1. **Separation of Concerns**
   - State: Pure data structure
   - Tools: Reusable functions with clear interfaces
   - Nodes: Orchestration logic only
   - Graph: Flow control

2. **Budget Awareness**
   - Real-time tracking of queries/pages/time
   - Pre-flight checks before tool execution
   - Forced termination on exhaustion

3. **Transparency**
   - Agent thoughts recorded for every decision
   - Tool call history with costs
   - Termination reason always provided

4. **Extensibility**
   - Tool registry for easy additions
   - Prompt templates for customization
   - State schema accommodates new fields

## Agent Behavior

The agent follows this decision pattern:

1. **Explore company website first** (discover_urls → crawl)
   - Most accurate source for company info
   - Cheapest in terms of API costs

2. **External search for verification** (serp → crawl)
   - Confirm findings from multiple sources
   - Higher confidence with cross-validation

3. **AI Overview for protected sites** (ai_overview)
   - Fallback when direct crawl blocked
   - Glassdoor, G2, Capterra, etc.

4. **Terminate when sufficient** (TERMINATE)
   - Quality score >= 0.9 + min sources met
   - OR budget exhausted
   - OR max iterations (10)

## Next Steps

To implement Phase 2, start with:

1. **tools.py** - Implement `serp_tool` using existing `SerpAdapter`
2. **tools.py** - Implement `crawl_tool` using existing `CrawlAdapter`
3. **tools.py** - Implement `discover_urls_tool` with sitemap parser
4. **nodes.py** - Implement `node_agent_reasoning` with LLM call
5. **Test end-to-end** with simple query

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for detailed implementation guide (to be created).
