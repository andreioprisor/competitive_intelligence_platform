import json
from typing import Any, Dict, List, Tuple
import logging

def _coerce_tool_args(args: Any) -> Dict[str, Any]:
    """Args may be dicts or JSON strings; normalize to dict."""
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            return json.loads(args)
        except Exception:
            return {"_raw": args}
    return {"_raw": args}


def _maybe_json(s: Any):
    """Try to parse stringified JSON; otherwise return as-is."""
    if isinstance(s, str):
        try:
            return json.loads(s)
        except Exception:
            return s
    return s


def _tool_sig(name: str, args: Dict[str, Any], id_: str = None) -> Tuple[str, str]:
    """
    Build a deduplication signature for a tool call.
    Prefer id when present; else fallback to name+sorted-args JSON.
    """
    if id_:
        return ("id", id_)
    try:
        return ("sig", f"{name}|{json.dumps(args, sort_keys=True, separators=(',',':'))}")
    except Exception:
        # if args not JSON-serializable
        return ("sig", f"{name}|{repr(args)}")


def _result_sig(name: str, tool_call_id: str, result: Any) -> Tuple[str, str]:
    """
    Build a deduplication signature for a tool result.
    Prefer tool_call_id; else fallback to name+result JSON hash-ish string.
    """
    if tool_call_id:
        return ("id", tool_call_id)
    try:
        return ("sig", f"{name}|{json.dumps(result, sort_keys=True, separators=(',',':'))}")
    except Exception:
        return ("sig", f"{name}|{repr(result)}")


def parse_logged_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse your logged 'task' chunk into a normalized dict:
    - messages: ordered list of {role, content, tool_call?, tool_calls? (deduped), tool_result?}
    - tool_calls: list of unique {name, args, id?}
    - tool_results: list of unique {name, result, tool_call_id?}
    - final_ai_message: last non-empty assistant text
    - structured_response: Final synthesis response from the agent (if present)
    - tools_used: set of tool names that were called
    """
    out = {
        "step": chunk.get("step"),
        "timestamp": chunk.get("timestamp"),
        "task_type": chunk.get("type"),
        "node_name": chunk.get("payload", {}).get("name"),
        "messages": [],
        "tool_calls": [],
        "tool_results": [],
        "final_ai_message": None,
        "structured_response": None,
        "tools_used": set(),
    }

    # Seen sets for deduplication
    seen_tool_calls = set()     # of _tool_sig
    seen_tool_results = set()   # of _result_sig

    payload = chunk.get("payload", {})
    input_ = payload.get("input", {})
    messages = input_.get("messages", [])

    def push_msg(role, content, extra=None):
        m = {"role": role, "content": content}
        if extra:
            m.update(extra)
        out["messages"].append(m)
        return m

    for m in messages:
        # Case 1: Plain dict (usually human)
        if isinstance(m, dict) and m.get("type") == "human":
            push_msg("human", m.get("content", ""))

        # Case 2: String-dumped message
        elif isinstance(m, str):
            push_msg("assistant" if ("THOUGHT:" in m or "ACTION:" in m or "OBSERVATION:" in m) else "unknown", m)

        else:
            # Likely LangChain message objects
            cls = getattr(m, "__class__", type(m)).__name__

            # ---- AIMessage ----
            if cls == "AIMessage":
                content = getattr(m, "content", "") or ""
                extra = {}

                # Extract usage metadata if present
                usage = getattr(m, "usage_metadata", None)
                if usage:
                    extra["usage_metadata"] = usage

                # (a) OpenAI-style single function_call in additional_kwargs
                add_kwargs = getattr(m, "additional_kwargs", {}) or {}
                function_call = add_kwargs.get("function_call")
                if isinstance(function_call, dict):
                    name = function_call.get("name")
                    args = _coerce_tool_args(function_call.get("arguments"))
                    sig = _tool_sig(name, args, id_=None)
                    if sig not in seen_tool_calls:
                        seen_tool_calls.add(sig)
                        tc = {"name": name, "args": args}
                        out["tool_calls"].append(tc)
                        if name:
                            out["tools_used"].add(name)
                        extra["tool_call"] = tc  # single

                push_msg("assistant", content, extra)
                if content.strip():
                    out["final_ai_message"] = content

            # ---- ToolMessage ----
            elif cls == "ToolMessage":
                tool_name = getattr(m, "name", None) or getattr(m, "tool_name", None)
                tool_call_id = getattr(m, "tool_call_id", None)
                raw_content = getattr(m, "content", None)
                result = _maybe_json(raw_content)

                sig = _result_sig(tool_name, tool_call_id, result)
                if sig not in seen_tool_results:
                    seen_tool_results.add(sig)
                    tr = {"name": tool_name, "result": result}
                    if tool_call_id is not None:
                        tr["tool_call_id"] = tool_call_id
                    out["tool_results"].append(tr)
                    if tool_name:
                        out["tools_used"].add(tool_name)

                # Also keep chronological message stream
                push_msg("tool", result, {"name": tool_name, "tool_call_id": tool_call_id})

            else:
                # Fallback
                role = getattr(m, "type", None) or getattr(m, "role", "unknown")
                content = getattr(m, "content", None)
                push_msg(role, content)

    # Optionally: if your logger sometimes puts results directly under payload['result'],
    # add handling here (kept as pass in your original).
    # result = payload.get("result")
    # if isinstance(result, list):
    #     ...

    # Calculate aggregate metrics
    total_tokens = 0
    input_tokens = 0
    output_tokens = 0
    reasoning_tokens = 0
    llm_calls = 0

    for msg in out["messages"]:
        if msg.get("role") == "assistant" and "usage_metadata" in msg:
            usage = msg["usage_metadata"]
            total_tokens += usage.get("total_tokens", 0)
            input_tokens += usage.get("input_tokens", 0)
            output_tokens += usage.get("output_tokens", 0)

            # Extract reasoning tokens if present
            output_details = usage.get("output_token_details", {})
            if isinstance(output_details, dict):
                reasoning_tokens += output_details.get("reasoning", 0)

            llm_calls += 1

    # Extract unique URLs crawled
    urls_crawled = set()
    for tr in out["tool_results"]:
        if tr.get("name") == "crawl":
            result = tr.get("result", [])
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and "url" in item:
                        urls_crawled.add(item["url"])
    logging.info("Tools used set: %s", out["tools_used"])

    # Extract search queries
    queries_executed = []
    for tc in out["tool_calls"]:
        if tc.get("name") == "serp":
            args = tc.get("args", {})
            queries = args.get("queries", [])
            if isinstance(queries, list):
                queries_executed.extend(queries)

    # Add aggregate metrics to output
    out["metrics"] = {
        "total_tokens": total_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "llm_calls": llm_calls,
        "tool_calls_count": len(out["tool_calls"]),
        "tool_results_count": len(out["tool_results"]),
        "urls_crawled": list(urls_crawled),
        "urls_crawled_count": len(urls_crawled),
        "queries_executed": queries_executed,
        "queries_count": len(queries_executed)
    }

    # Extract structured_response from the chunk (if it's a final result from agent.invoke())
    # The structured_response is typically at the top level of the state/chunk
    out["structured_response"] = chunk.get("structured_response")

    # Extract final answer from finalize tool result
    final_answer = None
    for msg in out["messages"]:
        if msg.get("role") == "tool" and msg.get("name") == "finalize":
            content = msg.get("content", {})
            if isinstance(content, dict):
                reasoning = content.get("reasoning", "")
                if reasoning:
                    final_answer = reasoning
                    break  # Take the first finalize result

    out["final_answer"] = final_answer

    # Convert tools_used set to list for JSON serialization
    out["tools_used"] = list(out["tools_used"])

    return out


def pack_messages_for_synthesis(state: Dict[str, Any]) -> tuple[List[Dict[str, str]], set[str]]:
    """
    Pack messages from state history into a conversation flow for synthesis.

    Uses parse_logged_chunk to parse messages, then truncates long markdowns
    from crawl tool results to keep context manageable.

    Args:
        state: State dict containing messages history

    Returns:
        Tuple of (packed_messages, tools_used_set) where:
        - packed_messages: List of message dicts with {role, content} for synthesis LLM call
        - tools_used_set: Set of tool names that were called during the conversation
    """
    logging.info("Packing messages for synthesis")
    MAX_MARKDOWN_CHARS = 5000  # Truncate each URL's markdown to this length

    # Create a chunk structure for parse_logged_chunk
    chunk = {
        "type": "synthesis_prep",
        "payload": {
            "input": {
                "messages": state.get("messages", [])
            }
        }
    }

    # Parse messages using existing robust parser
    parsed = parse_logged_chunk(chunk)
    logging.info(f"Parsed {len(parsed['messages'])} messages from state for synthesis packing")

    # Extract tools used from parsed chunk (already converted to list in parse_logged_chunk)
    tools_used = set(parsed.get("tools_used", []))

    # Check if finalize tool was called - if so, use ONLY that message
    finalize_result = None
    for msg in parsed["messages"]:
        if msg.get("role") == "tool" and msg.get("name") == "finalize":
            finalize_result = msg
            break

    # If finalize found with valid content, return ONLY that
    if finalize_result:
        finalize_content = finalize_result.get("content", "")
        # Ensure it has substantial content (>100 chars)
        if finalize_content and len(str(finalize_content)) > 100:
            logging.info("✅ Finalize tool detected - using ONLY finalize reasoning for synthesis")

            # Format content
            if isinstance(finalize_content, (dict, list)):
                try:
                    content_str = json.dumps(finalize_content, ensure_ascii=False, indent=2)
                except (TypeError, ValueError):
                    content_str = str(finalize_content)
            else:
                content_str = str(finalize_content)

            return ([{
                "role": "tool",
                "content": f"[Agent's Final Reasoning from finalize tool]\n{content_str}"
            }], tools_used)

    logging.info("❌ No valid finalize detected - using full message pack for synthesis")

    # Build packed messages from parsed output
    packed = []

    for i, msg in enumerate(parsed["messages"]):
        try:
            role = msg.get("role")
            content = msg.get("content")

            # Special handling for tool messages with crawl results
            if role == "tool" and msg.get("name") == "crawl":
                # Content might be a list of dicts with markdown fields
                if isinstance(content, list):
                    # Truncate markdown in each item
                    truncated_content = []
                    for item in content:
                        if isinstance(item, dict):
                            item_copy = item.copy()
                            if "markdown" in item_copy and isinstance(item_copy["markdown"], str):
                                markdown = item_copy["markdown"]
                                if len(markdown) > MAX_MARKDOWN_CHARS:
                                    item_copy["markdown"] = markdown[:MAX_MARKDOWN_CHARS] + f"\n\n... [truncated {len(markdown) - MAX_MARKDOWN_CHARS} chars]"
                            truncated_content.append(item_copy)
                        else:
                            truncated_content.append(item)
                    content = truncated_content

            # Format content for LLM
            if isinstance(content, (dict, list)):
                try:
                    content_str = json.dumps(content, ensure_ascii=False, indent=2)
                except (TypeError, ValueError) as e:
                    # JSON serialization failed - fall back to string
                    print(f"Warning: JSON serialization failed for message {i}: {e}")
                    content_str = str(content)
            else:
                content_str = str(content) if content is not None else ""

            # Add tool name prefix for tool messages
            if role == "tool" and msg.get("name"):
                content_str = f"[Tool: {msg['name']}]\n{content_str}"

            # Add tool calls info for assistant messages (if present in msg)
            if role == "assistant":
                # Check if this message has tool_calls metadata
                if msg.get("tool_call"):
                    # Single tool call
                    tc = msg["tool_call"]
                    if content_str:
                        content_str = f"{content_str}\n\n[Called tool: {tc.get('name', 'unknown')}]"
                    else:
                        content_str = f"[Called tool: {tc.get('name', 'unknown')}]"

            packed.append({
                "role": role,
                "content": content_str
            })

        except Exception as e:
            # Log the error and skip this message
            print(f"Error processing message {i} in pack_messages_for_synthesis: {e}")
            print(f"Problematic message: {msg}")
            # Add a placeholder message to maintain conversation flow
            packed.append({
                "role": msg.get("role", "unknown"),
                "content": f"[Error processing message: {str(e)}]"
            })
            continue

    return (packed, tools_used)
