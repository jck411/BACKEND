"""
Shared utilities for handling streaming LLM responses.

Following PROJECT_RULES.md:
- Single responsibility: Stream processing utilities
- Provider-agnostic tool call fragment stitching
- Type-safe with Pydantic models
"""

from typing import Any, Dict, List, Optional

from .models import CompletedToolCall


def _is_call_final(tc: Any, provider: str) -> bool:
    """
    Determine if a tool call chunk represents the final fragment.

    Args:
        tc: Tool call chunk from provider
        provider: Provider name ("openai", "anthropic", "gemini", etc.)

    Returns:
        True if this chunk completes the tool call
    """
    if provider == "anthropic":
        return getattr(tc, "is_final", False)

    # Gemini: one-shot => every chunk is final
    if provider == "gemini":
        return True

    # OpenAI, OpenRouter, and default: check for finish_reason
    return getattr(tc, "finish_reason", None) is not None


def merge_tool_chunks(
    delta_tool_calls: Optional[List[Any]], scratch: Dict[str, Dict[str, str]], *, provider: str
) -> List[CompletedToolCall]:
    """
    Merge streaming tool call fragments into completed calls.

    Takes raw delta.tool_calls from a single streaming chunk and accumulates
    fragments using id (if present) or index as the key. Returns any newly
    completed calls and removes them from the scratch buffer.

    Args:
        delta_tool_calls: Raw tool_calls list from streaming chunk (can be None)
        scratch: Per-turn scratch dict for accumulating fragments
        provider: Provider name for completion detection logic

    Returns:
        List of newly completed tool calls

    Example:
        scratch = {}

        # First chunk
        completed = merge_tool_chunks(
            [ToolCall(id="call_1", function=Function(name="get_weather", arguments='{"ci'))],
            scratch,
            provider="openai"
        )
        # Returns: [] (not complete yet)
        # scratch now contains: {"call_1": {"id": "call_1", "name": "get_weather", "arguments": '{"ci'}}

        # Second chunk
        completed = merge_tool_chunks(
            [ToolCall(id="call_1", function=Function(arguments='ty": "NYC"}', finish_reason="stop"))],
            scratch,
            provider="openai"
        )
        # Returns: [CompletedToolCall(id="call_1", name="get_weather", arguments='{"city": "NYC"}')]
        # scratch is now empty
    """
    completed = []

    for tc in delta_tool_calls or []:
        # Use id if present, otherwise fall back to index
        # This handles all mainstream providers: OpenAI, Anthropic, Gemini, etc.
        key = getattr(tc, "id", None) or getattr(tc, "index", None)

        # Special handling for providers that don't provide id/index on all chunks
        if key is None:
            if provider in ["openai", "openrouter"]:
                # For OpenAI: fragments after first chunk often lack id
                # Use the first available key in scratch (continuing existing tool call)
                if scratch:
                    key = list(scratch.keys())[0]
                else:
                    # Fallback: create a default key for first chunk without id
                    key = "tool_call_0"
            else:
                # For other providers, skip chunks without identifiers
                continue

        # Initialize or get existing entry in scratch buffer
        entry = scratch.setdefault(
            key, {"id": getattr(tc, "id", "") or f"auto_{key}", "name": "", "arguments": ""}
        )

        # Accumulate function name and arguments
        if hasattr(tc, "function") and tc.function:
            if hasattr(tc.function, "name") and tc.function.name:
                entry["name"] = str(tc.function.name) if tc.function.name is not None else ""
            if hasattr(tc.function, "arguments") and tc.function.arguments:
                entry["arguments"] += (
                    str(tc.function.arguments) if tc.function.arguments is not None else ""
                )

        # Check if this chunk completes the tool call
        if _is_call_final(tc, provider):
            # Ensure name is never None or empty
            final_name = entry["name"] if entry["name"] else "unknown_function"
            completed.append(
                CompletedToolCall(id=entry["id"], name=final_name, arguments=entry["arguments"])
            )
            scratch.pop(key, None)

    return completed


def finalize_remaining_calls(scratch: Dict[str, Dict[str, str]]) -> List[CompletedToolCall]:
    """
    Convert any remaining scratch entries to completed calls.

    Call this when the stream ends to handle cases where the final
    chunk didn't have explicit completion markers.

    Args:
        scratch: Scratch buffer with accumulated tool call fragments

    Returns:
        List of completed tool calls from remaining entries
    """
    completed = []

    for entry in scratch.values():
        # Ensure name is never None or empty
        final_name = entry["name"] if entry["name"] else "unknown_function"
        completed.append(
            CompletedToolCall(id=entry["id"], name=final_name, arguments=entry["arguments"])
        )

    scratch.clear()
    return completed
