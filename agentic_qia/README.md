# Agentic QIA - LangGraph Research Workflow

A LangGraph-based research agent that performs structured data collection about companies using ReAct reasoning and tool execution.

## Quick Start

### Prerequisites

1. Python 3.12+
2. Required environment variables in `.env`:
   ```
   OPENROUTER_API_KEY=your_key_here
   GEMINI_API_KEY=your_key_here
   SERP_API_KEY=your_key_here
   SCRAPINGDOG_API_KEY=your_key_here
   ```

### Running the Agent

```bash
# From project root
python3 -m agentic_qia.graph
```

The default example in `graph.py` researches cloud technologies used by emag.ro. Modify the `main()` function at the bottom of `graph.py` to customize:

```python
async def main():
    company_context = {
        "name": "Your Company",
        "domain": "example.com",
        "industry": "Technology",
        "size": "500-1000"
    }

    datapoint_context = {
        "dp_name": "Your Datapoint Name",
        "definition": "What you want to find out",
        "value_ranges": {
            "bad": "Description of bad case",
            "good": "Description of good case",
            "best": "Description of best case"
        }
    }

    graph = ReactGraph(company_context, datapoint_context)
    result = await graph.ainvoke(
        prompt="Your research question here"
    )
    return result

result = asyncio.run(main())
print(json.dumps(result, indent=2))
```

## Architecture

```
START → Triage → [ReAct Agent Loop] → Controller → Synthesis → END

[ReAct Agent Loop]:
  LLM Reasoning → Tool Execution → Message Updates
      ↑___________________|
         (loops until controller signals stop)
```

### Workflow Details

1. **Triage Node** (`node_triage` in `nodes.py`):
   - Analyzes the datapoint and company context
   - Creates a research plan with goal, instructions, and tool budgets
   - Uses OpenRouterAdapter to call LLM

2. **ReAct Agent Loop** (LangGraph built-in):
   - Executes tools based on the research plan
   - Reasons about next steps
   - Manages message history with pre/post hooks

4. **Synthesis Node** (`node_final_synthesis` in `nodes.py`):
   - Compiles all collected evidence
   - Generates structured response
   - Maps findings to datapoint value ranges

### Key Components

- **`graph.py`**: Main orchestration, ReactGraph class, workflow definition
- **`nodes.py`**: Node implementations (triage, controller, synthesis)
- **`tools.py`**: Tool wrappers that the LLM can call
- **`state.py`**: State schema for the graph
- **`agentic_adapters/`**: Backend implementations for tools (SERP, crawling, etc.)
- **`prompts/`**: Prompt templates for triage and synthesis

## Implementing New Tools

The system uses a two-layer architecture:
1. **Adapters** (`agentic_adapters/`) - Complex backend logic, API calls, data processing
2. **Tool wrappers** (`tools.py`) - LLM-friendly interfaces with budget tracking

### Existing Adapters

Already implemented in `agentic_adapters/`:
- **`serp_adapter.py`** - Google SERP API integration
- **`crawl_adapter.py`** - Web page content extraction
- **`llm_adapter.py`** - Gemini API for synthesis
- **`pages_synthesis_adapter.py`** - Multi-page summarization
- **`api_crawlers.py`** - ScrapingDog for protected pages

### Adding a New Tool

#### Step 1: Create Adapter (for complex logic only)

```python
# agentic_adapters/my_adapter.py
class MyAdapter:
    async def fetch_data(self, query: str) -> Dict:
        # API calls, processing, error handling
        return {"results": [...]}
```

#### Step 2: Create Tool Wrapper

```python
# tools.py
async def my_tool(query: str) -> str:
    """Tool description for LLM"""
    from agentic_adapters.my_adapter import MyAdapter

    adapter = MyAdapter()
    results = await adapter.fetch_data(query)

    # Format as markdown for LLM
    return f"### Results\n- {results}"
```

#### Step 3: Register with Budget Tracking

```python
# In create_budget_aware_tools()
async def my_tool_with_budget(query: str):
    thread_id = get_thread_id()
    BudgetManager.check_limits(thread_id)
    result = await my_tool(query)
    BudgetManager.inc(thread_id, my_resource=1)
    return result

tools.append(StructuredTool.from_function(
    coroutine=my_tool_with_budget,
    name="my_tool",
    description="When to use this tool"
))
```

#### Step 4: Update Budget System (if needed)

```python
# nodes.py - add new resource type
@dataclass
class Budget:
    my_resource: int

@dataclass
class Usage:
    my_resource: int = 0
```

#### Step 5: Document in Triage Prompt

```markdown
# prompts/triage.md
- my_tool: Description and when to use
- Budget: X for simple, Y for complex
```

## Best Practices

**Separation of Concerns**
- Adapters = Complex logic
- Tools = LLM formatting + budget

**LLM-Friendly Output**
- Markdown formatting
- Concise but informative
- No raw JSON

**Error Handling**
- Log errors clearly
- Return helpful messages
- Fail gracefully

**Async by Default**
- Enable parallel execution
- Use `async def` for all tools
